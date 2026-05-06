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

__all__ = [
    "TTSBaseConfig",
    "MockTTSConfig",
    "OpenAITTSConfig",
    "EdgeTTSConfig",
    "GLMTTSConfig",
    "ChatTTSConfig",
    "VibeVoiceTTSConfig",
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
    ],
    Field(discriminator="type")
]