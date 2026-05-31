"""TTS base configuration"""


from pydantic import Field

from ...core.base import ProviderConfig


class TTSBaseConfig(ProviderConfig):
    """
    TTS provider configuration base class

    All TTS provider configurations should inherit from this class
    """
    voice: str = Field(default="default", description="Voice / timbre")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed")
    api_key: str | None = Field(default=None, description="API Key")
