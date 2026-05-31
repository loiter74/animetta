"""
Animetta - Animated Narrative Intelligence & Messaging Assistant
一个富有灵魂的 AI 虚拟伴侣框架

名称来源：
- 意大利语 "animetta" = 小灵魂（anima 的爱称形式）
- 延续拉丁语 "anima" = 灵魂、生命力的精神内核
"""

__version__ = "0.1.0"
__author__ = "Animetta Team"

from .config import (
    AppConfig,
    ASRConfig,
    TTSConfig,
    LLMConfig,
    AgentConfig,
    PersonaConfig,
    SystemConfig,
)

from .core.service_context import ServiceContext
from .services import ASRInterface, TTSInterface, LLMInterface

__all__ = [
    "AppConfig",
    "ASRConfig",
    "TTSConfig",
    "LLMConfig",
    "AgentConfig",
    "PersonaConfig",
    "SystemConfig",
    "ServiceContext",
    "ASRInterface",
    "TTSInterface",
    "LLMInterface",
]
