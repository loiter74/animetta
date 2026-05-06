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

__all__ = [
    "TTSBaseConfig",
    "MockTTSConfig",
    "OpenAITTSConfig",
    "EdgeTTSConfig",
    "GLMTTSConfig",
    "ChatTTSConfig",
    "VibeVoiceTTSConfig",
    "KokoroTTSConfig",
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
    ],
    Field(discriminator="type")
]