"""
Expression Parameter Mapper Module

Converts emotions/expressions to Live2D model parameters
"""

from .base import ExpressionFrame, IEmotionParamMapper, ParameterState
from .emotion_param_mapper import DEFAULT_EMOTION_MAPPINGS, EmotionParamMapper

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
