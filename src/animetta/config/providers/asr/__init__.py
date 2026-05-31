"""ASR provider configuration module"""

from typing import Annotated, Union

from pydantic import Field

from .base import ASRBaseConfig
from .faster_whisper import FasterWhisperASRConfig
from .funasr import FunASRConfig
from .glm import GLMASRConfig
from .mock import MockASRConfig
from .openai import OpenAIASRConfig

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
    MockASRConfig | OpenAIASRConfig | GLMASRConfig | FasterWhisperASRConfig | FunASRConfig,
    Field(discriminator="type")
]
