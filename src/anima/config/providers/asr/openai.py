"""OpenAI ASR provider configuration"""

from typing import Optional, Literal
from pydantic import Field

from ...core.registry import ProviderRegistry
from .base import ASRBaseConfig


@ProviderRegistry.register("asr", "openai")
class OpenAIASRConfig(ASRBaseConfig):
    """OpenAI ASR (Whisper) configuration"""
    type: Literal["openai"] = "openai"
    model: str = Field(default="whisper-1", description="Whisper model name")
    base_url: Optional[str] = Field(default=None, description="API Base URL")