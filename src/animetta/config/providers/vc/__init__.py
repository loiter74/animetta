"""VC (Voice Conversion) provider configuration module"""

from typing import Annotated, Union
from pydantic import Field

from .base import VCBaseConfig
from .mock import MockVCConfig
from .rvc import RVCConfig

__all__ = [
    "VCBaseConfig",
    "MockVCConfig",
    "RVCConfig",
    "VCConfig",
]

# Discriminated Union type
VCConfig = Annotated[
    Union[
        MockVCConfig,
        RVCConfig,
    ],
    Field(discriminator="type")
]
