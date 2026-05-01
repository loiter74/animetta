"""DeepSeek LLM 提供者配置"""

from typing import Literal
from pydantic import Field

from ...core.registry import ProviderRegistry
from .base import LLMBaseConfig


@ProviderRegistry.register("llm", "deepseek")
class DeepSeekLLMConfig(LLMBaseConfig):
    """DeepSeek LLM 配置"""
    type: Literal["deepseek"] = "deepseek"
    model: str = Field(default="deepseek-v4-flash", description="模型名称: deepseek-v4-flash / deepseek-v4-pro")
    base_url: str = Field(default="https://api.deepseek.com/v1", description="DeepSeek API Base URL")
