"""
表情参数映射器模块

将情绪/表情转换为 Live2D 模型参数
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
    # 接口
    "IEmotionParamMapper",
    # 数据类
    "ParameterState",
    "ExpressionFrame",
    # 实现
    "EmotionParamMapper",
    # 常量
    "DEFAULT_EMOTION_MAPPINGS",
]
