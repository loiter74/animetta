"""
Animetta - Animated Narrative Intelligence & Messaging Assistant
一个富有灵魂的 AI 虚拟伴侣框架

名称来源：
- 意大利语 "animetta" = 小灵魂（anima 的爱称形式）
- 延续拉丁语 "anima" = 灵魂、生命力的精神内核
"""

__version__ = "0.1.0"
__author__ = "Animetta Team"

# Lazy imports to avoid ImportError when dependencies are not installed
# (e.g., during package installation or when running scripts that don't need all modules)
def __getattr__(name):
    if name in ("AgentConfig", "AppConfig", "ASRConfig", "LLMConfig", 
                "PersonaConfig", "SystemConfig", "TTSConfig"):
        from .config import (
            AgentConfig, AppConfig, ASRConfig, LLMConfig,
            PersonaConfig, SystemConfig, TTSConfig,
        )
        return locals()[name]
    elif name == "ServiceContext":
        from .core.service_context import ServiceContext
        return ServiceContext
    elif name in ("ASRInterface", "LLMInterface", "TTSInterface"):
        from .services import ASRInterface, LLMInterface, TTSInterface
        return locals()[name]
    raise AttributeError(f"module 'animetta' has no attribute {name!r}")

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
