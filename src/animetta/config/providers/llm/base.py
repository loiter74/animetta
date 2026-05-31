"""LLM base configuration"""


from pydantic import Field

from ...core.base import ProviderConfig


class LLMBaseConfig(ProviderConfig):
    """
    LLM provider configuration base class

    All LLM provider configurations should inherit from this class
    """
    api_key: str | None = Field(default=None, description="API Key")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Temperature parameter")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum generated tokens")
