"""Zhipu AI GLM TTS provider configuration"""

from typing import Literal

from pydantic import Field

from ...core.registry import ProviderRegistry
from .base import TTSBaseConfig


@ProviderRegistry.register("tts", "glm")
class GLMTTSConfig(TTSBaseConfig):
    """Zhipu AI GLM TTS configuration"""
    type: Literal["glm"] = "glm"
    model: str = Field(default="glm-tts", description="TTS model name")
    voice: str = Field(default="default", description="Voice / timbre")
    response_format: str = Field(default="wav", description="Audio format: wav/mp3")
    volume: float = Field(default=1.0, description="Volume: 0.0-2.0")
