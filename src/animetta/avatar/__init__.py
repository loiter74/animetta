"""
Live2D Module
Provides Live2D expression control based on emotional content.

The new architecture uses pluggable emotion analyzers and the strategy pattern.
"""

# New pluggable architecture
# Retained utility classes
from .analyzers.audio import AudioAnalyzer
from .analyzers.base import EmotionData, IEmotionAnalyzer
from .analyzers.llm_tag import EmotionExtractionResult, EmotionTag, StandaloneLLMTagAnalyzer
from .factory import (
    EmotionAnalyzerFactory,
    TimelineStrategyFactory,
    create_emotion_analyzer,
    create_timeline_strategy,
)

# Parameter mapper (new)
from .mappers.base import ExpressionFrame, IEmotionParamMapper, ParameterState
from .mappers.emotion_param_mapper import DEFAULT_EMOTION_MAPPINGS, EmotionParamMapper
from .prompts import EmotionPromptBuilder
from .strategies.base import ITimelineStrategy, TimelineSegment

__all__ = [
    # New architecture - analyzers
    "IEmotionAnalyzer",
    "EmotionData",
    "StandaloneLLMTagAnalyzer",
    "EmotionTag",
    "EmotionExtractionResult",
    # New architecture - strategies
    "ITimelineStrategy",
    "TimelineSegment",
    # New architecture - factory
    "EmotionAnalyzerFactory",
    "TimelineStrategyFactory",
    "create_emotion_analyzer",
    "create_timeline_strategy",
    # New architecture - parameter mapper
    "IEmotionParamMapper",
    "ParameterState",
    "ExpressionFrame",
    "EmotionParamMapper",
    "DEFAULT_EMOTION_MAPPINGS",
    # Utility classes
    "AudioAnalyzer",
    "EmotionPromptBuilder",
]
