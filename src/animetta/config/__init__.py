"""
Configuration module (refactored)
Uses plugin-based Provider architecture + Pydantic Discriminated Unions

Architecture:
- core/: Core infrastructure (BaseConfig, ProviderRegistry)
- providers/: Provider configurations (LLM/ASR/TTS implementations)
- agent.py: Agent configuration (combined LLM)
- persona.py: Persona configuration (includes avatar, etc.)
- system.py: System configuration
- app.py: Application configuration
"""

# Core
from .core.base import BaseConfig
from .core.registry import ProviderRegistry

# Providers - LLM
from .providers.llm import (
    LLMConfig,
    LLMBaseConfig,
    MockLLMConfig,
    OpenAILLMConfig,
    GLMLLMConfig,
    OllamaLLMConfig,
    DeepSeekLLMConfig,
)

# Providers - ASR
from .providers.asr import (
    ASRConfig,
    ASRBaseConfig,
    MockASRConfig,
    OpenAIASRConfig,
    GLMASRConfig,
)

# Providers - TTS
from .providers.tts import (
    TTSConfig,
    TTSBaseConfig,
    MockTTSConfig,
    OpenAITTSConfig,
    EdgeTTSConfig,
    GLMTTSConfig,
)

# Providers - VAD
from .providers.vad import (
    VADConfig,
    VADBaseConfig,
    MockVADConfig,
    SileroVADConfig,
)

# Composite configs
from .agent import AgentConfig
from .system import SystemConfig
from .persona import PersonaConfig, PersonalityTraits, BehaviorRules, MBTIProfile, MBTIDimensions, MBTIDimensionDelta
from .app import AppConfig

__all__ = [
    # Core
    "BaseConfig",
    "ProviderRegistry",
    # LLM Providers
    "LLMConfig",
    "LLMBaseConfig",
    "MockLLMConfig",
    "OpenAILLMConfig",
    "GLMLLMConfig",
    "OllamaLLMConfig",
    "DeepSeekLLMConfig",
    # ASR Providers
    "ASRConfig",
    "ASRBaseConfig",
    "MockASRConfig",
    "OpenAIASRConfig",
    "GLMASRConfig",
    # TTS Providers
    "TTSConfig",
    "TTSBaseConfig",
    "MockTTSConfig",
    "OpenAITTSConfig",
    "EdgeTTSConfig",
    "GLMTTSConfig",
    # VAD Providers
    "VADConfig",
    "VADBaseConfig",
    "MockVADConfig",
    "SileroVADConfig",
    # Composite
    "AgentConfig",
    "SystemConfig",
    # Persona
    "PersonaConfig",
    "PersonalityTraits",
    "BehaviorRules",
    # App
    "AppConfig",
]