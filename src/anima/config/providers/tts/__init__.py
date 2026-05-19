"""TTS provider configuration module"""

from typing import Annotated, Union
from pydantic import Field

from .base import TTSBaseConfig
from .mock import MockTTSConfig
from .openai import OpenAITTSConfig
from .edge import EdgeTTSConfig
from .glm import GLMTTSConfig
from .chattts import ChatTTSConfig
from .vibe_voice import VibeVoiceTTSConfig
from .kokoro import KokoroTTSConfig
from .gpt_sovits import GPTSoVITSConfig
from .qwen3 import Qwen3TTSConfig

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
    Union[
        MockTTSConfig,
        OpenAITTSConfig,
        EdgeTTSConfig,
        GLMTTSConfig,
        ChatTTSConfig,
        VibeVoiceTTSConfig,
        KokoroTTSConfig,
        GPTSoVITSConfig,
        Qwen3TTSConfig,
    ],
    Field(discriminator="type")
]