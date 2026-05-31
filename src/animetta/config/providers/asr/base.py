"""ASR base configuration"""


from pydantic import Field

from ...core.base import ProviderConfig


class ASRBaseConfig(ProviderConfig):
    """
    ASR provider configuration base class

    All ASR provider configurations should inherit from this class
    """
    language: str = Field(default="zh", description="Recognition language")
    api_key: str | None = Field(default=None, description="API Key")
