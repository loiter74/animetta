"""
表情参数映射器 - 基础接口
将情绪/表情转换为 Live2D 参数
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class ParameterState:
    """
    Live2D 参数状态

    Attributes:
        name: 参数名（如 ParamMouthOpenY）
        value: 参数值（通常范围 -1 到 1，或 0 到 1）
        duration: 过渡时长（秒）
    """
    name: str
    value: float
    duration: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "duration": self.duration
        }


@dataclass
class ExpressionFrame:
    """
    表情帧

    表示某一时刻的完整表情状态，包含多个参数。

    Attributes:
        parameters: 参数列表
        intensity: 整体强度（0.0 - 1.0）
        timestamp: 时间戳（秒）
    """
    parameters: List[ParameterState]
    intensity: float = 1.0
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameters": [p.to_dict() for p in self.parameters],
            "intensity": self.intensity,
            "timestamp": self.timestamp
        }


class IEmotionParamMapper(ABC):
    """
    情绪参数映射器接口

    将情绪标签映射到 Live2D 模型参数。

    设计模式:
    - Strategy Pattern: 不同的映射策略
    - Plugin Pattern: 可动态注册的映射器

    使用示例:
        >>> mapper = EmotionParamMapper()
        >>> frame = mapper.map_emotion("happy", intensity=0.8)
        >>> print(frame.parameters)
        [ParameterState('ParamMouthOpenY', 0.48, 0.3), ...]
    """

    @abstractmethod
    def map_emotion(
        self,
        emotion: str,
        intensity: float = 1.0,
        context: Optional[Dict[str, Any]] = None
    ) -> ExpressionFrame:
        """
        将情绪映射到 Live2D 参数

        Args:
            emotion: 情绪名称（如 "happy", "sad", "angry"）
            intensity: 强度（0.0 - 1.0）
            context: 可选上下文信息

        Returns:
            ExpressionFrame: 包含所有参数的表情帧

        Raises:
            ValueError: 不支持的情绪
        """
        pass

    @abstractmethod
    def map_emotions_timeline(
        self,
        emotions: List[tuple],  # [(emotion, start_time, end_time, intensity), ...]
        duration: float
    ) -> List[ExpressionFrame]:
        """
        将情绪时间轴映射到表情帧序列

        Args:
            emotions: 情绪片段列表
            duration: 总时长

        Returns:
            List[ExpressionFrame]: 表情帧序列
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """映射器名称"""
        pass

    def get_supported_emotions(self) -> List[str]:
        """获取支持的情绪列表"""
        return []

    def apply_intensity(self, base_value: float, intensity: float) -> float:
        """
        应用强度系数

        Args:
            base_value: 基础值
            intensity: 强度（0.0 - 1.0）

        Returns:
            float: 应用强度后的值
        """
        return base_value * intensity
