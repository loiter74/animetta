"""
Expression Parameter Mapper Module

Converts emotions/expressions to Live2D model parameters
"""

from .base import (
    IEmotionParamMapper,
    ParameterState,
    ExpressionFrame
)

from .emotion_param_mapper import (
    EmotionParamMapper,
    DEFAULT_EMOTION_MAPPINGS
)

__all__ = [
    # Interface
    "IEmotionParamMapper",
    # Data classes
    "ParameterState",
    "ExpressionFrame",
    # Implementation
    "EmotionParamMapper",
    # Constants
    "DEFAULT_EMOTION_MAPPINGS",
]
