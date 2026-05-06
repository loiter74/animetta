"""ASR provider configuration module"""

from typing import Annotated, Union
from pydantic import Field

from .base import ASRBaseConfig
from .mock import MockASRConfig
from .openai import OpenAIASRConfig
from .glm import GLMASRConfig
from .faster_whisper import FasterWhisperASRConfig
from .funasr import FunASRConfig

__all__ = [
    "ASRBaseConfig",
    "MockASRConfig",
    "OpenAIASRConfig",
    "GLMASRConfig",
    "FasterWhisperASRConfig",
    "FunASRConfig",
    "ASRConfig",
]

# Discriminated Union type
ASRConfig = Annotated[
    Union[
        MockASRConfig,
        OpenAIASRConfig,
        GLMASRConfig,
        FasterWhisperASRConfig,
        FunASRConfig,
    ],
    Field(discriminator="type")
]