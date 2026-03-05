"""
数据处理工具
准备训练数据集
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import hashlib

from loguru import logger
from tqdm import tqdm
from sklearn.model_selection import train_test_split


@dataclass
class ProcessedSample:
    """处理后的样本"""
    input: str
    output: str
    metadata: Dict


class DataProcessor:
    """数据处理工具"""

    def __init__(
        self,
        seed: int = 42,
        max_samples: Optional[int] = None,
    ):
        self.seed = seed
        self.max_samples = max_samples

    def load_raw_data(self, path: str) -> List[Dict]:
        """加载原始数据"""
        path = Path(path)
        if not path.exists():
                raise FileNotFoundError(f"Data file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # 支持多种数据格式
        if isinstance(data, dict):
            if "data" in data:
                return data["data"]
            elif "samples" in data:
                return data["samples"]
            elif "conversations" in data:
                return data["conversations"]
            else:
                return [data]
        elif isinstance(data, list):
            return data
        else:
                raise ValueError(f"Unsupported data format in {path}")

    def validate_sample(self, sample: Dict) -> bool:
        """验证样本格式"""
        # 必须字段
        if "input" not in sample and "output" not in sample:
            return False

        # 检查字段不为空
        if not sample["input"] or not sample["output"]:
            return False

        # 检查长度合理
        if len(sample["input"]) < 1 or len(sample["output"]) < 1:
            return False

        if len(sample["input"]) > 2000 or len(sample["output"]) > 2000:
            return False

        return True

    def filter_duplicates(
        self,
        samples: List[Dict],
        hash_key: str = "input",
    ) -> List[Dict]:
        """过滤重复样本"""
        seen = set()
        unique_samples = []

        for sample in samples:
            # 计算hash
            content = sample.get(hash_key, "")
            h = hashlib.md5(content.encode()).hexdigest()

            if h not in seen:
                seen.add(h)
                unique_samples.append(sample)

        if len(unique_samples) < len(samples):
            logger.info(f"Removed {len(samples) - len(unique_samples)} duplicate samples")

        return unique_samples

    def balance_dataset(
        self,
        samples: List[Dict],
        max_samples: Optional[int] = None,
    ) -> List[Dict]:
        """平衡数据集（如果需要采样到固定数量）"""
        if max_samples is not None and len(samples) > max_samples:
            random.seed(self.seed)
            samples = random.sample(samples, max_samples)
            logger.info(f"Sampled {max_samples} samples from {len(samples)} total")

        return samples

    def split_dataset(
        self,
        samples: List[Dict],
        val_ratio: float = 0.1,
        test_ratio: float = 0.0,
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """划分数据集"""
        # 随机打乱
        random.seed(self.seed)
        shuffled = samples.copy()
        random.shuffle(shuffled)

        # 计算划分点
        n = len(shuffled)
        val_size = int(n * val_ratio)
        test_size = int(n * test_ratio)

        # 划分
        val_data = shuffled[:val_size]
        test_data = shuffled[val_size:val_size + test_size]
        train_data = shuffled[val_size + test_size:]

        logger.info(f"Dataset split: train={len(train_data)}, val={len(val_data)}, test={len(test_data)}")

        return train_data, val_data, test_data

    def save_dataset(
        self,
        samples: List[Dict],
        output_path: str,
    ) -> None:
        """保存数据集"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(samples)} samples to {output_path}")

    def process(
        self,
        input_path: str,
        output_dir: str,
        val_ratio: float = 0.1,
        test_ratio: float = 0.0,
    ) -> Dict[str, int]:
        """处理数据的完整流程"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 加载数据
        logger.info(f"Loading data from {input_path}")
        samples = self.load_raw_data(input_path)
        logger.info(f"Loaded {len(samples)} raw samples")

        # 验证
        valid_samples = [s for s in tqdm(samples, desc="Validating") if self.validate_sample(s)]
        logger.info(f"Valid samples: {len(valid_samples)}/{len(samples)}")

        # 过滤重复
        unique_samples = self.filter_duplicates(valid_samples)
        logger.info(f"Unique samples: {len(unique_samples)}")

        # 平衡
        balanced_samples = self.balance_dataset(unique_samples, self.max_samples)

        # 划分
        train_data, val_data, test_data = self.split_dataset(
            balanced_samples,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
        )

        # 保存
        self.save_dataset(train_data, output_dir / "train.json")
        self.save_dataset(val_data, output_dir / "val.json")
        if test_data:
            self.save_dataset(test_data, output_dir / "test.json")

        return {
            "total": len(samples),
            "valid": len(valid_samples),
            "unique": len(unique_samples),
            "train": len(train_data),
            "val": len(val_data),
            "test": len(test_data) if test_data else 0,
        }

