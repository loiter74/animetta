"""VAD provider configuration module"""

from typing import Annotated, Union

from pydantic import Field

from .base import VADBaseConfig
from .mock import MockVADConfig
from .silero import SileroVADConfig

__all__ = [
    "VADBaseConfig",
    "MockVADConfig",
    "SileroVADConfig",
    "VADConfig",
]

# Discriminated Union type
VADConfig = Annotated[
    MockVADConfig | SileroVADConfig,
    Field(discriminator="type")
]
