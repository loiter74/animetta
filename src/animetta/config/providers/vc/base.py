"""Voice Conversion (VC) base configuration"""

from pydantic import Field

from ...core.base import ProviderConfig


class VCBaseConfig(ProviderConfig):
    """
    Voice Conversion provider configuration base class

    All VC provider configurations should inherit from this class.
    Voice conversion transforms the timbre of an input audio while
    preserving the linguistic content.
    """
    device: str = Field(default="cuda:0", description="Device for inference (cuda:0 / cpu)")
    is_half: bool = Field(default=True, description="Use FP16 half precision for inference")
