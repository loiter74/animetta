"""Audio Source Separation provider configuration module"""

from typing import Annotated, Union
from pydantic import Field

from .base import SeparationBaseConfig
from .mock import MockSeparationConfig
from .demucs import DemucsSeparationConfig

__all__ = [
    "SeparationBaseConfig",
    "MockSeparationConfig",
    "DemucsSeparationConfig",
    "SeparationConfig",
]

# Discriminated Union type
SeparationConfig = Annotated[
    Union[
        MockSeparationConfig,
        DemucsSeparationConfig,
    ],
    Field(discriminator="type")
]
