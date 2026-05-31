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
# Composite configs
from .agent import AgentConfig
from .app import AppConfig
from .core.base import BaseConfig
from .core.registry import ProviderRegistry
from .persona import (
    BehaviorRules,
    MBTIDimensionDelta,
    MBTIDimensions,
    MBTIProfile,
    PersonaConfig,
    PersonalityTraits,
)

# Providers - ASR
from .providers.asr import (
    ASRBaseConfig,
    ASRConfig,
    GLMASRConfig,
    MockASRConfig,
    OpenAIASRConfig,
)

# Providers - LLM
from .providers.llm import (
    DeepSeekLLMConfig,
    GLMLLMConfig,
    LLMBaseConfig,
    LLMConfig,
    MockLLMConfig,
    OllamaLLMConfig,
    OpenAILLMConfig,
)

# Providers - TTS
from .providers.tts import (
    EdgeTTSConfig,
    GLMTTSConfig,
    MockTTSConfig,
    OpenAITTSConfig,
    TTSBaseConfig,
    TTSConfig,
)

# Providers - VAD
from .providers.vad import (
    MockVADConfig,
    SileroVADConfig,
    VADBaseConfig,
    VADConfig,
)
from .system import SystemConfig

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
