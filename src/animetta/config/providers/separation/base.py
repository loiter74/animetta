"""Audio Source Separation base configuration"""

from typing import Optional
from pydantic import Field

from ...core.base import ProviderConfig


class SeparationBaseConfig(ProviderConfig):
    """
    Audio Source Separation provider configuration base class

    All separation provider configurations should inherit from this class.
    Source separation decomposes an audio mixture into its constituent
    stems (e.g., vocals, drums, bass, other).
    """
    device: str = Field(default="cuda:0", description="Device for inference (cuda:0 / cpu)")
    sample_rate: int = Field(default=44100, description="Target sample rate for processing")
