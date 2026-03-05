"""
数据处理流水线
Data Processing Pipeline for Large-scale Style Transfer Dataset

支持:
- 大规模数据处理 (E盘)
- 断点续传
- 并行风格清除
- 数据验证和清洗
"""

import os
import json
import hashlib
import argparse
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

from loguru import logger
from tqdm import tqdm, async_tqdm


@dataclass
class PipelineConfig:
    """数据流水线配置"""
    # 路径配置
    data_root: str = "E:/anima_data"
    raw_dir: str = "raw"
    processed_dir: str = "processed"
    cache_dir: str = "cache"
    checkpoint_dir: str = "checkpoints"

    # 处理配置
    batch_size: int = 100                  # 每批处理数量
    max_workers: int = 8                   # 并行工作线程数
    checkpoint_interval: int = 1000        # 检查点保存间隔

    # API 配置
    api_provider: str = "glm"              # glm / openai
    api_model: str = "glm-4-flash"
    api_max_retries: int = 3
    api_retry_delay: float = 1.0

    # 数据配置
    val_ratio: float = 0.1
    max_samples: Optional[int] = None
    seed: int = 42

    # 风格描述
    style_description: str = "中性、通用、正式的助手风格"

    def __post_init__(self):
        """初始化路径"""
        self.data_root = Path(self.data_root)
        self.raw_path = self.data_root / self.raw_dir
        self.processed_path = self.data_root / self.processed_dir
        self.cache_path = self.data_root / self.cache_dir
        self.checkpoint_path = self.data_root / self.checkpoint_dir

        # 创建目录
        for path in [self.raw_path, self.processed_path, self.cache_path, self.checkpoint_path]:
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class ProcessCheckpoint:
    """处理检查点"""
    processed_hashes: Set[str] = field(default_factory=set)
    failed_hashes: Set[str] = field(default_factory=set)
    total_processed: int = 0
    total_failed: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict:
        return {
            "processed_hashes": list(self.processed_hashes),
            "failed_hashes": list(self.failed_hashes),
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ProcessCheckpoint":
        return cls(
            processed_hashes=set(data.get("processed_hashes", [])),
            failed_hashes=set(data.get("failed_hashes", [])),
            total_processed=data.get("total_processed", 0),
            total_failed=data.get("total_failed", 0),
            last_updated=data.get("last_updated", ""),
        )


class DataPipeline:
    """
    大规模数据处理流水线

    目录结构:
    E:/anima_data/
    ├── raw/                    # 原始数据
    │   ├── source1.json
    │   ├── source2.jsonl
    │   └── ...
    ├── processed/              # 处理后的数据
    │   ├── train.json
    │   ├── val.json
    │   └── all.json
    ├── cache/                  # 中间缓存
    │   ├── cleaned/            # 风格清除后的数据
    │   └── temp/
    └── checkpoints/            # 断点续传检查点
        └── pipeline_checkpoint.json
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.checkpoint = ProcessCheckpoint()
        self._cleaner = None
        self._lock = threading.Lock()

        # 设置日志
        self._setup_logging()

    def _setup_logging(self):
        """设置日志"""
        log_file = self.config.data_root / "pipeline.log"
        logger.add(log_file, rotation="100 MB", retention="7 days")

    @property
    def cleaner(self):
        """延迟初始化风格清除器"""
        if self._cleaner is None:
            import os
            if self.config.api_provider == "glm":
                from zhipuai import ZhipuAI
                api_key = os.getenv("GLM_API_KEY")
                if not api_key:
                    raise ValueError("GLM_API_KEY not set")
                self._cleaner = ZhipuAI(api_key=api_key)
            elif self.config.api_provider == "openai":
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not set")
                self._cleaner = openai.OpenAI(api_key=api_key)
        return self._cleaner

    def _build_clean_prompt(self, text: str) -> str:
        """构建风格清除prompt"""
        return f"""请将以下文本改写为{self.config.style_description}。

要求:
1. 保持原意不变
2. 移除所有个性化的表达方式、语气词、口头禅
3. 使用标准、通用的表达方式
4. 不要添加任何emoji或表情标签

原文:
{text}

改写后的文本（直接输出，不要解释）:"""

    def clean_style(self, text: str) -> Optional[str]:
        """清除单个文本的风格"""
        prompt = self._build_clean_prompt(text)

        for attempt in range(self.config.api_max_retries):
            try:
                if self.config.api_provider == "glm":
                    response = self.cleaner.chat.completions.create(
                        model=self.config.api_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=512,
                    )
                else:  # openai
                    response = self.cleaner.chat.completions.create(
                        model=self.config.api_model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=512,
                    )

                cleaned = response.choices[0].message.content.strip()

                # 验证结果
                if not cleaned or len(cleaned) < 5:
                    raise ValueError("Empty or too short response")

                return cleaned

            except Exception as e:
                logger.warning(f"Clean attempt {attempt + 1} failed: {e}")
                if attempt < self.config.api_max_retries - 1:
                    import time
                    time.sleep(self.config.api_retry_delay)

        return None

    def load_checkpoint(self) -> bool:
        """加载检查点"""
        checkpoint_file = self.config.checkpoint_path / "pipeline_checkpoint.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.checkpoint = ProcessCheckpoint.from_dict(data)
                logger.info(f"Loaded checkpoint: {self.checkpoint.total_processed} processed, {self.checkpoint.total_failed} failed")
                return True
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        return False

    def save_checkpoint(self):
        """保存检查点"""
        self.checkpoint.last_updated = datetime.now().isoformat()
        checkpoint_file = self.config.checkpoint_path / "pipeline_checkpoint.json"

        with self._lock:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(self.checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

    def get_text_hash(self, text: str) -> str:
        """计算文本hash"""
        return hashlib.md5(text.encode()).hexdigest()

    def load_raw_data(self, file_path: Path) -> List[Dict]:
        """加载原始数据文件"""
        data = []

        if file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list):
                    data = content
                elif isinstance(content, dict) and "data" in content:
                    data = content["data"]
                else:
                    data = [content]

        elif file_path.suffix == ".jsonl":
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))

        return data

    def process_batch(
        self,
        batch: List[Dict],
        text_field: str = "output",
    ) -> List[Dict]:
        """处理一批数据"""
        results = []

        for item in batch:
            original_text = item.get(text_field, "")
            if not original_text:
                continue

            text_hash = self.get_text_hash(original_text)

            # 检查是否已处理
            with self._lock:
                if text_hash in self.checkpoint.processed_hashes:
                    # 从缓存加载
                    cache_file = self.config.cache_path / "cleaned" / f"{text_hash}.json"
                    if cache_file.exists():
                        with open(cache_file, "r", encoding="utf-8") as f:
                            cached = json.load(f)
                            results.append({
                                "input": cached["cleaned"],
                                "output": original_text,
                            })
                            continue

            # 清除风格
            cleaned_text = self.clean_style(original_text)

            if cleaned_text:
                # 缓存结果
                cache_file = self.config.cache_path / "cleaned" / f"{text_hash}.json"
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"cleaned": cleaned_text, "original": original_text}, f, ensure_ascii=False)

                results.append({
                    "input": cleaned_text,
                    "output": original_text,
                })

                with self._lock:
                    self.checkpoint.processed_hashes.add(text_hash)
                    self.checkpoint.total_processed += 1
            else:
                with self._lock:
                    self.checkpoint.failed_hashes.add(text_hash)
                    self.checkpoint.total_failed += 1

        return results

    def run(
        self,
        input_files: Optional[List[str]] = None,
        text_field: str = "output",
    ):
        """
        运行数据处理流水线

        Args:
            input_files: 输入文件列表 (None则处理raw目录下所有文件)
            text_field: 要处理的文本字段名
        """
        # 加载检查点
        self.load_checkpoint()

        # 获取输入文件
        if input_files:
            files = [Path(f) for f in input_files]
        else:
            files = list(self.config.raw_path.glob("*.json")) + \
                    list(self.config.raw_path.glob("*.jsonl"))

        if not files:
            logger.error("No input files found")
            return

        logger.info(f"Found {len(files)} input files")

        all_results = []

        for file_path in files:
            logger.info(f"Processing: {file_path}")

            # 加载数据
            data = self.load_raw_data(file_path)
            logger.info(f"Loaded {len(data)} samples from {file_path.name}")

            # 分批处理
            for i in tqdm(range(0, len(data), self.config.batch_size), desc=f"Processing {file_path.name}"):
                batch = data[i:i + self.config.batch_size]
                results = self.process_batch(batch, text_field)
                all_results.extend(results)

                # 保存检查点
                if (i // self.config.batch_size) % (self.config.checkpoint_interval // self.config.batch_size) == 0:
                    self.save_checkpoint()

                    # 保存中间结果
                    self._save_intermediate_results(all_results)

            self.save_checkpoint()

        # 最终保存
        self._save_final_results(all_results)

        logger.info(f"Pipeline completed!")
        logger.info(f"Total processed: {self.checkpoint.total_processed}")
        logger.info(f"Total failed: {self.checkpoint.total_failed}")

    def _save_intermediate_results(self, results: List[Dict]):
        """保存中间结果"""
        temp_file = self.config.cache_path / "temp" / "intermediate.json"
        temp_file.parent.mkdir(parents=True, exist_ok=True)

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    def _save_final_results(self, results: List[Dict]):
        """保存最终结果"""
        import random

        # 去重
        seen = set()
        unique_results = []
        for item in results:
            h = self.get_text_hash(item["output"])
            if h not in seen:
                seen.add(h)
                unique_results.append(item)

        logger.info(f"Unique samples: {len(unique_results)}")

        # 限制数量
        if self.config.max_samples and len(unique_results) > self.config.max_samples:
            random.seed(self.config.seed)
            unique_results = random.sample(unique_results, self.config.max_samples)

        # 划分数据集
        random.seed(self.config.seed)
        random.shuffle(unique_results)

        val_size = int(len(unique_results) * self.config.val_ratio)
        val_data = unique_results[:val_size]
        train_data = unique_results[val_size:]

        # 保存
        self._save_json(train_data, self.config.processed_path / "train.json")
        self._save_json(val_data, self.config.processed_path / "val.json")
        self._save_json(unique_results, self.config.processed_path / "all.json")

        logger.info(f"Saved: train={len(train_data)}, val={len(val_data)}, all={len(unique_results)}")

    def _save_json(self, data: List[Dict], path: Path):
        """保存JSON文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="数据处理流水线")
    parser.add_argument("--data-root", "-d", type=str, default="E:/anima_data",
                        help="数据根目录")
    parser.add_argument("--input", "-i", type=str, nargs="+", default=None,
                        help="输入文件 (不指定则处理raw目录下所有文件)")
    parser.add_argument("--text-field", "-t", type=str, default="output",
                        help="要处理的文本字段名")
    parser.add_argument("--batch-size", "-b", type=int, default=100,
                        help="批处理大小")
    parser.add_argument("--max-workers", "-w", type=int, default=8,
                        help="并行工作线程数")
    parser.add_argument("--val-ratio", "-v", type=float, default=0.1,
                        help="验证集比例")
    parser.add_argument("--max-samples", "-m", type=int, default=None,
                        help="最大样本数")
    parser.add_argument("--style-description", "-s", type=str,
                        default="中性、通用、正式的助手风格",
                        help="目标风格描述")
    parser.add_argument("--api-provider", "-p", type=str, default="glm",
                        choices=["glm", "openai"], help="API提供商")
    parser.add_argument("--api-model", type=str, default="glm-4-flash",
                        help="API模型名称")

    args = parser.parse_args()

    config = PipelineConfig(
        data_root=args.data_root,
        batch_size=args.batch_size,
        max_workers=args.max_workers,
        val_ratio=args.val_ratio,
        max_samples=args.max_samples,
        style_description=args.style_description,
        api_provider=args.api_provider,
        api_model=args.api_model,
    )

    pipeline = DataPipeline(config)
    pipeline.run(input_files=args.input, text_field=args.text_field)


if __name__ == "__main__":
    main()
