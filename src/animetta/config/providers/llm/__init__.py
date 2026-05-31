"""LLM provider configuration module"""

from typing import Annotated, Union

from pydantic import Field

from .base import LLMBaseConfig
from .deepseek import DeepSeekLLMConfig
from .glm import GLMLLMConfig
from .local_lora_llm import LocalLoraLLMConfig
from .mock import MockLLMConfig
from .ollama import OllamaLLMConfig
from .openai import OpenAILLMConfig

# Export all configuration classes
__all__ = [
    "LLMBaseConfig",
    "MockLLMConfig",
    "OpenAILLMConfig",
    "GLMLLMConfig",
    "OllamaLLMConfig",
    "LocalLoraLLMConfig",
    "DeepSeekLLMConfig",
    "LLMConfig",
]

# Discriminated Union type - Pydantic will automatically select the correct class based on the type field
LLMConfig = Annotated[
    MockLLMConfig | OpenAILLMConfig | GLMLLMConfig | OllamaLLMConfig | LocalLoraLLMConfig | DeepSeekLLMConfig,
    Field(discriminator="type")
]
