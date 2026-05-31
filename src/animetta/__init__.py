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

# Lazy imports — tolerate failures for lightweight consumers (e.g. memory_v2)
try:
    from .core.service_context import ServiceContext
except Exception:
    ServiceContext = None  # type: ignore[assignment]

try:
    from .services import ASRInterface, TTSInterface, LLMInterface
except Exception:
    ASRInterface = None  # type: ignore[assignment]
    TTSInterface = None  # type: ignore[assignment]
    LLMInterface = None  # type: ignore[assignment]

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
