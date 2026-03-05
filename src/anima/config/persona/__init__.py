"""
人设配置模块

包含基础人设配置和增强人设构建器
"""

from .base import (
    PersonalityTraits,
    BehaviorRules,
    PersonaConfig,
)
from .enhanced import (
    EnhancedPersonaBuilder,
    create_enhanced_system_prompt,
)

__all__ = [
    'PersonalityTraits',
    'BehaviorRules',
    'PersonaConfig',
    'EnhancedPersonaBuilder',
    'create_enhanced_system_prompt',
]
