"""VibeVoice TTS 提供者配置 (Microsoft 开源长文本多说话人 TTS)"""

from typing import Literal, Optional
from pydantic import Field

from ...core.registry import ProviderRegistry
from .base import TTSBaseConfig


@ProviderRegistry.register("tts", "vibe_voice")
class VibeVoiceTTSConfig(TTSBaseConfig):
    """VibeVoice TTS 配置

    支持 Local（本地 GPU 推理）和 Remote（HTTP API）两种模式。
    默认 Remote 模式指向本地 localhost:8765 的 VibeVoice 推理服务。
    RTX 5090D 可流畅运行 1.5B (~6GB VRAM) 和 7B (~16GB VRAM) 模型。
    """
    type: Literal["vibe_voice"] = "vibe_voice"

    # === 模型标识 ===
    model: str = Field(
        default="vibe-voice-1.5b",
        description="模型名称标识（用于日志和远程 API 请求）",
    )

    # === 部署模式 ===
    mode: str = Field(
        default="remote",
        description='部署模式: "remote"（HTTP API）或 "local"（本地 subprocess 推理）',
    )

    # === Remote 模式参数 ===
    base_url: str = Field(
        default="http://localhost:8765",
        description="Remote 模式: VibeVoice 推理服务地址",
    )

    # === Local 模式参数 ===
    model_size: str = Field(
        default="1.5b",
        description='Local 模式: 模型大小 "1.5b" 或 "7b"',
    )
    model_path: Optional[str] = Field(
        default=None,
        description="Local 模式: 模型权重路径（默认 HuggingFace 自动下载）",
    )
    device: str = Field(
        default="cuda:0",
        description="Local 模式: 推理设备 cuda:0 / cpu",
    )

    # === 合成参数 ===
    voice: str = Field(
        default="default",
        description="默认音色名称",
    )
    num_speakers: int = Field(
        default=1,
        ge=1,
        le=4,
        description="说话人数 (VibeVoice 支持最多 4 speaker)",
    )
    language: str = Field(
        default="zh",
        description='语言: "zh" / "en" / "mix"',
    )
