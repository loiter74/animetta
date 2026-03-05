"""
风格转换数据模块
PyTorch Lightning DataModule for Style Transfer
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import torch
from torch.utils.data import Dataset, DataLoader
from pytorch_lightning import LightningDataModule

from transformers import AutoTokenizer, PreTrainedTokenizer


class StyleTransferDataset(Dataset):
    """风格转换数据集"""

    def __init__(
        self,
        data_path: str,
        tokenizer: PreTrainedTokenizer,
        max_source_length: int = 256,
        max_target_length: int = 256,
        style_name: str = "custom",
        style_description: str = "",
    ):
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.style_name = style_name
        self.style_description = style_description

        # 加载数据
        self.data = self._load_data(data_path)
        print(f"Loaded {len(self.data)} samples from {data_path}")

    def _load_data(self, path: str) -> List[Dict]:
        """加载数据文件"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 支持多种数据格式
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return data

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        item = self.data[idx]
        source_text = item["input"]   # 中性文本
        target_text = item["output"]  # 目标风格文本

        # 构建 prompt
        prompt = self._build_prompt(source_text)
        full_text = prompt + target_text + self.tokenizer.eos_token

        # Tokenize
        # 对于 decoder-only 模型，我们需要：
        # 1. 将整个序列 tokenize
        # 2. 创建 labels，其中 prompt 部分为 -100（不计算loss）

        # 先 tokenize prompt 以确定 prompt 长度
        prompt_ids = self.tokenizer(
            prompt,
            add_special_tokens=False,
            return_tensors="pt"
        )["input_ids"][0]
        prompt_length = len(prompt_ids)

        # Tokenize 完整序列
        full_encodings = self.tokenizer(
            full_text,
            max_length=self.max_source_length + self.max_target_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        input_ids = full_encodings["input_ids"][0]
        attention_mask = full_encodings["attention_mask"][0]

        # 创建 labels：prompt 部分设为 -100
        labels = input_ids.clone()
        labels[:prompt_length] = -100

        # Padding 部分也设为 -100
        labels[attention_mask == 0] = -100

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

    def _build_prompt(self, source_text: str) -> str:
        """构建输入 prompt"""
        # Qwen2.5 Chat 格式
        system_prompt = "你是一个风格转换助手。"
        if self.style_description:
            system_prompt += f"\n请将输入的文本转换为{self.style_name}风格。\n风格特点：{self.style_description}"
        else:
            system_prompt += f"\n请将输入的文本转换为{self.style_name}风格。"

        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n将以下文本转换风格：\n{source_text}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        return prompt


class StyleTransferDataModule(LightningDataModule):
    """风格转换数据模块"""

    def __init__(
        self,
        config: "StyleTransferConfig",
        tokenizer: Optional[PreTrainedTokenizer] = None,
    ):
        super().__init__()
        self.config = config
        self.tokenizer = tokenizer

        # 计算完整路径
        self.data_root = Path(config.data.data_root)
        self.processed_dir = self.data_root / "processed"
        self.train_file = self.processed_dir / config.data.train_file
        self.val_file = self.processed_dir / config.data.val_file

        self.train_dataset: Optional[StyleTransferDataset] = None
        self.val_dataset: Optional[StyleTransferDataset] = None

    def setup(self, stage: Optional[str] = None):
        """设置数据集"""
        # 延迟加载tokenizer
        if self.tokenizer is None:
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model.base_model,
                cache_dir=self.config.model.cache_dir,
                trust_remote_code=True,
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = "<|endoftext|>"

        if stage == "fit" or stage is None:
            self.train_dataset = StyleTransferDataset(
                data_path=str(self.train_file),
                tokenizer=self.tokenizer,
                max_source_length=self.config.training.max_source_length,
                max_target_length=self.config.training.max_target_length,
                style_name=self.config.style_name,
                style_description=self.config.style_description,
            )

            self.val_dataset = StyleTransferDataset(
                data_path=str(self.val_file),
                tokenizer=self.tokenizer,
                max_source_length=self.config.training.max_source_length,
                max_target_length=self.config.training.max_target_length,
                style_name=self.config.style_name,
                style_description=self.config.style_description,
            )

    def train_dataloader(self) -> DataLoader:
        return DataLoader(
            self.train_dataset,
            batch_size=self.config.training.batch_size,
            shuffle=True,
            num_workers=self.config.data.num_workers,
            pin_memory=True,
            drop_last=True,
        )

    def val_dataloader(self) -> DataLoader:
        return DataLoader(
            self.val_dataset,
            batch_size=self.config.training.batch_size,
            shuffle=False,
            num_workers=self.config.data.num_workers,
            pin_memory=True,
        )


# ============================================
# 数据处理工具
# ============================================

@dataclass
class StyleCleanerConfig:
    """风格清除配置"""
    api_type: str = "glm"  # glm / openai
    model: str = "glm-4-flash"
    api_key_env: str = "GLM_API_KEY"
    temperature: float = 0.3
    max_tokens: int = 512


class StyleCleaner:
    """
    使用 API LLM 清除文本风格
    将目标风格文本转换为中性/通用风格
    """

    CLEAN_SYSTEM_PROMPT = """你是一个文本风格标准化助手。
你的任务是将输入文本转换为标准、中性的助手风格，移除原文中的：
- 特殊的说话习惯和口癖
- 情绪化的表达
- 特殊的语气词
- 网络用语和梗

保留原文的核心信息和意图，用简洁、标准的中文表达。"""

    CLEAN_USER_PROMPT = """请将以下文本转换为标准中性风格，只输出转换后的文本：

{source_text}"""

    def __init__(self, config: StyleCleanerConfig):
        self.config = config
        self._client = None

    @property
    def client(self):
        """延迟初始化 API 客户端"""
        if self._client is None:
            import os
            if self.config.api_type == "glm":
                from zhipuai import ZhipuAI
                self._client = ZhipuAI(api_key=os.getenv(self.config.api_key_env))
            elif self.config.api_type == "openai":
                import openai
                self._client = openai.OpenAI(api_key=os.getenv(self.config.api_key_env))
            else:
                raise ValueError(f"Unsupported API type: {self.config.api_type}")
        return self._client

    def clean(self, text: str) -> str:
        """清除文本风格，返回中性文本"""
        if self.config.api_type == "glm":
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.CLEAN_SYSTEM_PROMPT},
                    {"role": "user", "content": self.CLEAN_USER_PROMPT.format(source_text=text)},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content.strip()

        elif self.config.api_type == "openai":
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self.CLEAN_SYSTEM_PROMPT},
                    {"role": "user", "content": self.CLEAN_USER_PROMPT.format(source_text=text)},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return response.choices[0].message.content.strip()

        else:
            raise ValueError(f"Unsupported API type: {self.config.api_type}")

    def process_dataset(
        self,
        input_file: str,
        output_file: str,
        text_field: str = "output",
        input_field: str = "input",
    ) -> None:
        """
        处理数据集：为目标风格文本生成对应的中性文本

        输入文件格式 (原始风格对话):
        [
            {"output": "目标风格文本1"},
            {"output": "目标风格文本2"},
            ...
        ]

        输出文件格式 (配对数据):
        [
            {"input": "中性文本1", "output": "目标风格文本1"},
            {"input": "中性文本2", "output": "目标风格文本2"},
            ...
        ]
        """
        import json
        from tqdm import tqdm

        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []
        for item in tqdm(data, desc="Cleaning style"):
            target_text = item[text_field]

            # 如果已有中性文本，直接使用
            if input_field in item and item[input_field]:
                neutral_text = item[input_field]
            else:
                # 调用 API 清除风格
                neutral_text = self.clean(target_text)

            results.append({
                "input": neutral_text,
                "output": target_text,
            })

        # 保存结果
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"Processed {len(results)} samples, saved to {output_file}")
