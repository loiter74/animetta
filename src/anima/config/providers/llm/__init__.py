"""LLM provider configuration module"""

from typing import Annotated, Union
from pydantic import Field

from .base import LLMBaseConfig
from .mock import MockLLMConfig
from .openai import OpenAILLMConfig
from .glm import GLMLLMConfig
from .ollama import OllamaLLMConfig
from .local_lora_llm import LocalLoraLLMConfig
from .deepseek import DeepSeekLLMConfig

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
    Union[MockLLMConfig, OpenAILLMConfig, GLMLLMConfig, OllamaLLMConfig, LocalLoraLLMConfig, DeepSeekLLMConfig],
    Field(discriminator="type")
]