"""
Persona configuration module

Contains base persona configuration and enhanced persona builder
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
