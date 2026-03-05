"""
风格清除工具
使用 API LLM 将文本转换为中性风格
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

from loguru import logger
from tqdm import tqdm


@dataclass
class CleanResult:
    """风格清除结果"""
    original: str           # 原始文本
    cleaned: str            # 清除后的中性文本
    success: bool           # 是否成功
    error: Optional[str]    # 错误信息


class StyleCleaner(ABC):
    """风格清除基类"""

    def __init__(
        self,
        style_description: str = "中性、通用、正式的助手风格",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.style_description = style_description
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @abstractmethod
    async def clean_single(self, text: str) -> CleanResult:
        """清除单个文本的风格"""
        pass

    def clean_batch(
        self,
        texts: List[str],
        max_workers: int = 4,
        show_progress: bool = True,
    ) -> List[CleanResult]:
        """批量清除风格"""
        results = []

        # 使用线程池进行并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def process_all():
                tasks = [self.clean_single(text) for text in texts]
                return await asyncio.gather(*tasks)

            if show_progress:
                # 带进度条的处理
                iterator = tqdm(texts, desc="Cleaning style")
                for text in iterator:
                    result = loop.run_until_complete(self.clean_single(text))
                    results.append(result)
            else:
                results = loop.run_until_complete(process_all())

            loop.close()

        return results


class GLMStyleCleaner(StyleCleaner):
    """使用 GLM API 进行风格清除"""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4-flash",
        style_description: str = "中性、通用、正式的助手风格",
        **kwargs,
    ):
        super().__init__(style_description, **kwargs)
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from zhipuai import ZhipuAI
                self._client = ZhipuAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("Please install zhipuai: pip install zhipuai")
        return self._client

    def _build_prompt(self, text: str) -> str:
        """构建清除风格的 prompt"""
        return f"""请将以下文本改写为{self.style_description}。
要求：
1. 保持原意不变
2. 移除所有个性化的表达方式、语气词、口头禅
3. 使用标准、通用的表达方式
4. 不要添加任何emoji或表情标签

原文：
{text}

改写后的文本（直接输出，不要解释）："""

    async def clean_single(self, text: str) -> CleanResult:
        """清除单个文本的风格"""
        import time

        prompt = self._build_prompt(text)

        for attempt in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=512,
                    )

                    cleaned_text = response.choices[0].message.content.strip()

                    # 验证结果
                    if not cleaned_text or len(cleaned_text) < 5:
                        raise ValueError("Empty or too short response")

                    return CleanResult(
                        original=text,
                        cleaned=cleaned_text,
                        success=True,
                        error=None,
                    )

                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        return CleanResult(
                            original=text,
                            cleaned="",
                            success=False,
                            error=str(e),
                        )

        return CleanResult(
            original=text,
            cleaned="",
            success=False,
            error="Max retries exceeded",
        )


class OpenAIStyleCleaner(StyleCleaner):
    """使用 OpenAI API 进行风格清除"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        style_description: str = "中性、通用、正式的助手风格",
        **kwargs,
    ):
        super().__init__(style_description, **kwargs)
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    @property
    def client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                kwargs = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        return self._client

    def _build_prompt(self, text: str) -> str:
        """构建清除风格的 prompt"""
        return f"""Please rewrite the following text in a {self.style_description}.

Requirements:
1. Keep the original meaning unchanged
2. Remove all personalized expressions, tone words, and catchphrases
3. Use standard, common expressions
4. Do not add any emojis or expression tags

Original text:
{text}

Rewritten text (output directly, no explanation):"""

    async def clean_single(self, text: str) -> CleanResult:
        """清除单个文本的风格"""
        import time

        prompt = self._build_prompt(text)

        for attempt in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=512,
                    )

                    cleaned_text = response.choices[0].message.content.strip()

                    if not cleaned_text or len(cleaned_text) < 5:
                        raise ValueError("Empty or too short response")

                    return CleanResult(
                        original=text,
                        cleaned=cleaned_text,
                        success=True,
                        error=None,
                    )

                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        return CleanResult(
                            original=text,
                            cleaned="",
                            success=False,
                            error=str(e),
                        )

        return CleanResult(
            original=text,
            cleaned="",
            success=False,
            error="Max retries exceeded",
        )


def create_cleaner(
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    style_description: str = "中性、通用、正式的助手风格",
    **kwargs,
) -> StyleCleaner:
    """
    创建风格清除器

    Args:
        provider: 提供商 ("glm" / "openai")
        api_key: API密钥
        model: 模型名称 (可选)
        style_description: 目标风格描述
    """
    if provider == "glm":
        return GLMStyleCleaner(
            api_key=api_key,
            model=model or "glm-4-flash",
            style_description=style_description,
            **kwargs,
        )
    elif provider == "openai":
        return OpenAIStyleCleaner(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            style_description=style_description,
            **kwargs,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# 便捷函数
def clean_dataset(
    input_file: str,
    output_file: str,
    provider: str,
    api_key: str,
    text_field: str = "output",
    style_description: str = "中性、通用、正式的助手风格",
    max_workers: int = 4,
):
    """
    清洗数据集的风格

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        provider: API提供商
        api_key: API密钥
        text_field: 要清洗的文本字段名
        style_description: 目标风格描述
        max_workers: 并行工作线程数
    """
    cleaner = create_cleaner(
        provider=provider,
        api_key=api_key,
        style_description=style_description,
    )

    # 加载数据
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 提取文本
    texts = [item[text_field] for item in data]

    # 批量清洗
    results = cleaner.clean_batch(texts, max_workers=max_workers)

    # 构建输出数据
    output_data = []
    for item, tqdm(data):
        text = item[text_field]
        idx = data.index(item)
        result = results[idx]

        if result.success:
            output_data.append({
                "input": result.cleaned,  # 清洗后的中性文本
                "output": text,           # 原始目标风格文本
            })
        else:
            logger.warning(f"Failed to clean text: {result.error}")
            # 可以选择跳过或保留原始文本
            output_data.append({
                "input": text,  # 清洗失败，保留原文本
                "output": text,
            })

    # 保存结果
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Cleaned {len(output_data)} samples, saved to {output_file}")
    success_count = sum(1 for r in results if r.success)
    logger.info(f"Success rate: {success_count}/{len(results)}")


if __name__ == "__main__":
    import os

    # 示例用法
    api_key = os.getenv("GLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set GLM_API_KEY or OPENAI_API_KEY environment variable")
        exit(1)

    provider = "glm" if os.getenv("GLM_API_KEY") else "openai"

    clean_dataset(
        input_file="data/raw_dialogues.json",
        output_file="data/train.json",
        provider=provider,
        api_key=api_key,
        text_field="response",
        style_description="中性、通用、正式的助手风格",
        max_workers=4,
    )
