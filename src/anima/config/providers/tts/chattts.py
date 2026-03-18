"""ChatTTS 提供者配置"""

from typing import Literal, Optional
from pydantic import Field

from ...core.registry import ProviderRegistry
from .base import TTSBaseConfig


@ProviderRegistry.register("tts", "chattts")
class ChatTTSConfig(TTSBaseConfig):
    """ChatTTS 配置（开源对话式语音合成）"""
    type: Literal["chattts"] = "chattts"
    model_path: str = Field(
        default="E:/models/ChatTTS",
        description="模型文件存放路径"
    )
    device: str = Field(
        default="cpu",
        description="推理设备: cuda / cpu"
    )
    compile: bool = Field(
        default=False,
        description="是否启用 torch.compile（Windows 建议关闭）"
    )
    speaker_seed: Optional[int] = Field(
        default=42,
        description="说话人音色种子，固定后每次生成的声音一致；设为 None 则随机"
    )
    temperature: float = Field(
        default=0.3,
        description="生成温度，越低越稳定，越高越有表现力"
    )
    top_p: float = Field(
        default=0.7,
        description="nucleus sampling 参数"
    )
    top_k: int = Field(
        default=20,
        description="top-k sampling 参数"
    )
