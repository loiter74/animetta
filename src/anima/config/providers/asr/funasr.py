"""FunASR Paraformer ASR 提供者配置"""

from typing import Literal, Optional, List
from pydantic import Field

from ...core.registry import ProviderRegistry
from .base import ASRBaseConfig


@ProviderRegistry.register("asr", "funasr")
class FunASRConfig(ASRBaseConfig):
    """FunASR Paraformer 配置

    FunASR 是阿里开源的语音识别工具包，支持：
    - paraformer-zh: 中文离线语音识别（推荐）
    - paraformer-zh-streaming: 中文流式语音识别
    - paraformer-en: 英文语音识别

    特点：
    - 中文识别准确率比 Whisper 更高
    - 支持实时流式识别
    - 可选配 VAD、标点恢复、说话人分离
    """
    type: Literal["funasr"] = "funasr"

    # 模型配置
    model: str = Field(
        default="paraformer-zh",
        description="FunASR 模型名称 (paraformer-zh/paraformer-zh-streaming/paraformer-en)"
    )

    # 可选的辅助模型
    vad_model: Optional[str] = Field(
        default="fsmn-vad",
        description="VAD 模型 (fsmn-vad)，设为 null 禁用"
    )

    punc_model: Optional[str] = Field(
        default="ct-punc",
        description="标点恢复模型 (ct-punc)，设为 null 禁用"
    )

    spk_model: Optional[str] = Field(
        default=None,
        description="说话人识别模型 (cam++)，设为 null 禁用"
    )

    # 设备配置
    device: str = Field(
        default="cuda",
        description="运行设备 (cpu/cuda)"
    )

    ncpu: int = Field(
        default=4,
        ge=1,
        description="CPU 线程数（用于计算）"
    )

    # 流式识别参数
    chunk_size: List[int] = Field(
        default_factory=lambda: [0, 10, 5],
        description="流式识别块大小 [0, 10, 5] 表示首块0秒，后续每块10秒，5秒重叠"
    )

    # 热词功能
    hotword: Optional[str] = Field(
        default=None,
        description="热词文件路径或热词字符串"
    )

    # 模型缓存目录
    model_hub: str = Field(
        default="ms",  # ms = ModelScope, hf = HuggingFace
        description="模型下载源 (ms=ModelScope, hf=HuggingFace)"
    )

    disable_update: bool = Field(
        default=True,
        description="禁用模型自动更新检查"
    )
