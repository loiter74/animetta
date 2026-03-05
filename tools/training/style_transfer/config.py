"""
风格转换训练配置
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class LoRAConfig:
    """LoRA 配置"""
    r: int = 16                          # LoRA rank
    lora_alpha: int = 32                 # LoRA alpha (通常为 2*r)
    lora_dropout: float = 0.05           # Dropout
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])
    bias: str = "none"                   # none, all, lora_only


@dataclass
class TrainingConfig:
    """训练配置"""
    # 基础设置
    max_epochs: int = 3
    batch_size: int = 4                  # per device
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1

    # 序列长度
    max_source_length: int = 256         # 输入文本最大长度
    max_target_length: int = 256         # 输出文本最大长度

    # 优化
    optimizer: str = "adamw_torch"
    lr_scheduler: str = "cosine"
    precision: str = "bf16-mixed"        # fp16 / bf16-mixed / 32

    # 显存优化
    gradient_checkpointing: bool = True
    fp16_opt_level: str = "O2"

    # 日志
    log_every_n_steps: int = 10
    val_check_interval: float = 0.25     # 每个epoch验证4次


@dataclass
class ModelConfig:
    """模型配置"""
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    cache_dir: Optional[str] = None
    use_flash_attention: bool = True     # 推荐开启，节省显存


@dataclass
class DataConfig:
    """数据配置"""
    # 数据路径
    data_root: str = "E:/anima_data"          # 数据根目录 (E盘)
    train_file: str = "processed/train.json"
    val_file: str = "processed/val.json"

    # 原始数据
    raw_data_dir: str = "raw"                  # 原始数据目录
    cache_dir: str = "cache"                   # 缓存目录

    # 处理配置
    num_workers: int = 4
    preprocessing_num_workers: int = 8

    # 增量处理
    resume_from_checkpoint: bool = True        # 断点续传
    checkpoint_interval: int = 1000            # 每处理多少条保存一次


@dataclass
class StyleTransferConfig:
    """风格转换训练总配置"""
    # 子配置
    model: ModelConfig = field(default_factory=ModelConfig)
    lora: LoRAConfig = field(default_factory=LoRAConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    data: DataConfig = field(default_factory=DataConfig)

    # 路径
    output_dir: str = "outputs/style_transfer"
    seed: int = 42

    # 风格提示词模板（运行时填充）
    style_name: str = "custom"
    style_description: str = ""

    @classmethod
    def from_yaml(cls, path: str) -> "StyleTransferConfig":
        """从YAML文件加载配置"""
        import yaml
        from dataclasses import asdict

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        def dict_to_dataclass(d: dict, dataclass_type):
            """递归转换字典到dataclass"""
            if d is None:
                return dataclass_type()
            fields = {}
            for field_name, field_type in dataclass_type.__dataclass_fields__.items():
                if field_name in d:
                    value = d[field_name]
                    # 检查是否是嵌套的dataclass
                    if hasattr(field_type.type, "__dataclass_fields__"):
                        value = dict_to_dataclass(value, field_type.type)
                    fields[field_name] = value
            return dataclass_type(**fields)

        return StyleTransferConfig(
            model=dict_to_dataclass(data.get("model", {}), ModelConfig),
            lora=dict_to_dataclass(data.get("lora", {}), LoRAConfig),
            training=dict_to_dataclass(data.get("training", {}), TrainingConfig),
            data=dict_to_dataclass(data.get("data", {}), DataConfig),
            output_dir=data.get("output_dir", "outputs/style_transfer"),
            seed=data.get("seed", 42),
            style_name=data.get("style_name", "custom"),
            style_description=data.get("style_description", ""),
        )

    def to_yaml(self, path: str) -> None:
        """保存配置到YAML文件"""
        import yaml
        from dataclasses import asdict

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(asdict(self), f, allow_unicode=True, default_flow_style=False)
