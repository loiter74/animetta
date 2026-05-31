"""Audio Source Separation provider configuration module"""

from typing import Annotated, Union

from pydantic import Field

from .base import SeparationBaseConfig
from .demucs import DemucsSeparationConfig
from .mock import MockSeparationConfig

__all__ = [
    "SeparationBaseConfig",
    "MockSeparationConfig",
    "DemucsSeparationConfig",
    "SeparationConfig",
]

# Discriminated Union type
SeparationConfig = Annotated[
    MockSeparationConfig | DemucsSeparationConfig,
    Field(discriminator="type")
]
