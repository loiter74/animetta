"""VAD base configuration"""

from typing import Literal
from ...core.base import BaseConfig


class VADBaseConfig(BaseConfig):
    """VAD configuration base class"""
    type: str = "base"
    sample_rate: int = 16000