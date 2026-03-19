"""
Live2D 模块
提供基于情感内容的 Live2D 表情控制

新架构使用插件式情绪分析器和策略模式。
"""

# 新的插件式架构
from .analyzers.base import IEmotionAnalyzer, EmotionData
from .analyzers.llm_tag import (
    StandaloneLLMTagAnalyzer,
    EmotionTag,
    EmotionExtractionResult
)
from .strategies.base import ITimelineStrategy, TimelineSegment
from .factory import (
    EmotionAnalyzerFactory,
    TimelineStrategyFactory,
    create_emotion_analyzer,
    create_timeline_strategy,
)

# 参数映射器（新增）
from .mappers.base import (
    IEmotionParamMapper,
    ParameterState,
    ExpressionFrame
)
from .mappers.emotion_param_mapper import (
    EmotionParamMapper,
    DEFAULT_EMOTION_MAPPINGS
)

# 保留的工具类
from .analyzers.audio import AudioAnalyzer
from .prompts import EmotionPromptBuilder

__all__ = [
    # 新架构 - 分析器
    "IEmotionAnalyzer",
    "EmotionData",
    "StandaloneLLMTagAnalyzer",
    "EmotionTag",
    "EmotionExtractionResult",
    # 新架构 - 策略
    "ITimelineStrategy",
    "TimelineSegment",
    # 新架构 - 工厂
    "EmotionAnalyzerFactory",
    "TimelineStrategyFactory",
    "create_emotion_analyzer",
    "create_timeline_strategy",
    # 新架构 - 参数映射器
    "IEmotionParamMapper",
    "ParameterState",
    "ExpressionFrame",
    "EmotionParamMapper",
    "DEFAULT_EMOTION_MAPPINGS",
    # 工具类
    "AudioAnalyzer",
    "EmotionPromptBuilder",
]
