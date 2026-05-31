"""TTS provider configuration module"""

from typing import Annotated, Union

from pydantic import Field

from .base import TTSBaseConfig
from .chattts import ChatTTSConfig
from .edge import EdgeTTSConfig
from .glm import GLMTTSConfig
from .gpt_sovits import GPTSoVITSConfig
from .kokoro import KokoroTTSConfig
from .mock import MockTTSConfig
from .openai import OpenAITTSConfig
from .qwen3 import Qwen3TTSConfig
from .vibe_voice import VibeVoiceTTSConfig

__all__ = [
    "TTSBaseConfig",
    "MockTTSConfig",
    "OpenAITTSConfig",
    "EdgeTTSConfig",
    "GLMTTSConfig",
    "ChatTTSConfig",
    "VibeVoiceTTSConfig",
    "KokoroTTSConfig",
    "GPTSoVITSConfig",
    "Qwen3TTSConfig",
    "TTSConfig",
]

# Discriminated Union type
TTSConfig = Annotated[
    MockTTSConfig | OpenAITTSConfig | EdgeTTSConfig | GLMTTSConfig | ChatTTSConfig | VibeVoiceTTSConfig | KokoroTTSConfig | GPTSoVITSConfig | Qwen3TTSConfig,
    Field(discriminator="type")
]
