"""
情绪参数映射器 - 默认实现
将常见情绪映射到 Live2D 模型参数
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from .base import (
    IEmotionParamMapper,
    ExpressionFrame,
    ParameterState
)


# 默认情绪参数映射配置
DEFAULT_EMOTION_MAPPINGS = {
    "happy": {
        # 嘴巴：微笑
        "ParamMouthOpenY": 0.6,
        "ParamMouthForm": 0.3,
        # 眉毛：上扬
        "ParamEyebrowLY": 0.4,
        "ParamEyebrowRY": 0.4,
        # 眼睛：睁大，有神
        "ParamEyeLOpen": 0.95,
        "ParamEyeROpen": 0.95,
        "ParamEyeBallX": 0.0,
        "ParamEyeBallY": -0.1,
        # 头部：微微上扬
        "ParamAngleX": -0.05,
        "ParamAngleY": 0.0,
        "ParamAngleZ": 0.0,
        # 身体：轻微前倾
        "ParamBodyAngleX": 0.05,
    },

    "sad": {
        # 嘴巴：微张，嘴角下垂
        "ParamMouthOpenY": 0.2,
        "ParamMouthForm": -0.2,
        # 眉毛：下压，内收
        "ParamEyebrowLY": -0.3,
        "ParamEyebrowRY": -0.3,
        # 眼睛：半闭
        "ParamEyeLOpen": 0.6,
        "ParamEyeROpen": 0.6,
        # 头部：低垂
        "ParamAngleX": 0.15,
        "ParamAngleY": 0.0,
    },

    "angry": {
        # 嘴巴：紧闭或微张
        "ParamMouthOpenY": 0.3,
        "ParamMouthForm": 0.1,
        # 眉毛：紧锁，下压
        "ParamEyebrowLY": -0.6,
        "ParamEyebrowRY": -0.6,
        # 眼睛：怒目而视
        "ParamEyeLOpen": 0.8,
        "ParamEyeROpen": 0.8,
        # 头部：前倾，微侧
        "ParamAngleX": -0.1,
        "ParamAngleY": 0.15,
        "ParamAngleZ": 0.1,
    },

    "surprised": {
        # 嘴巴：张开
        "ParamMouthOpenY": 0.7,
        "ParamMouthForm": 0.0,
        # 眉毛：上扬
        "ParamEyebrowLY": 0.5,
        "ParamEyebrowRY": 0.5,
        # 眼睛：睁大
        "ParamEyeLOpen": 1.0,
        "ParamEyeROpen": 1.0,
        # 头部：后仰
        "ParamAngleX": -0.15,
        "ParamAngleY": 0.0,
    },

    "neutral": {
        # 默认状态
        "ParamMouthOpenY": 0.0,
        "ParamEyebrowLY": 0.0,
        "ParamEyebrowRY": 0.0,
        "ParamEyeLOpen": 0.85,
        "ParamEyeROpen": 0.85,
        "ParamAngleX": 0.0,
        "ParamAngleY": 0.0,
        "ParamAngleZ": 0.0,
    },

    "thinking": {
        # 嘴巴：微张
        "ParamMouthOpenY": 0.15,
        # 眉毛：一高一低（思考状）
        "ParamEyebrowLY": -0.2,
        "ParamEyebrowRY": 0.1,
        # 眼睛：向上看
        "ParamEyeLOpen": 0.7,
        "ParamEyeROpen": 0.7,
        "ParamEyeBallY": 0.3,
        # 头部：侧倾，低垂
        "ParamAngleX": 0.1,
        "ParamAngleY": -0.1,
        "ParamAngleZ": 0.15,
    },

    "confused": {
        # 嘴巴：歪斜
        "ParamMouthOpenY": 0.2,
        "ParamMouthForm": 0.3,
        # 眉毛：内收
        "ParamEyebrowLY": 0.2,
        "ParamEyebrowRY": 0.2,
        # 眼睛：眯眼
        "ParamEyeLOpen": 0.7,
        "ParamEyeROpen": 0.7,
        # 头部：侧倾
        "ParamAngleZ": 0.2,
    },

    "love": {
        # 嘴巴：温柔微笑
        "ParamMouthOpenY": 0.4,
        "ParamMouthForm": 0.2,
        # 眉毛：柔和上扬
        "ParamEyebrowLY": 0.2,
        "ParamEyebrowRY": 0.2,
        # 眼睛：温柔注视
        "ParamEyeLOpen": 0.8,
        "ParamEyeROpen": 0.8,
        "ParamEyeBallY": -0.1,
        # 头部：微侧
        "ParamAngleY": -0.1,
    },

    "shy": {
        # 嘴巴：抿嘴
        "ParamMouthOpenY": 0.1,
        "ParamMouthForm": 0.1,
        # 眉毛：低垂
        "ParamEyebrowLY": -0.1,
        "ParamEyebrowRY": -0.1,
        # 眼睛：向下看
        "ParamEyeLOpen": 0.7,
        "ParamEyeROpen": 0.7,
        "ParamEyeBallY": 0.4,
        # 头部：低垂，侧转
        "ParamAngleX": 0.2,
        "ParamAngleY": 0.15,
    },

    "excited": {
        # 嘴巴：大笑
        "ParamMouthOpenY": 0.8,
        "ParamMouthForm": 0.4,
        # 眉毛：高扬
        "ParamEyebrowLY": 0.6,
        "ParamEyebrowRY": 0.6,
        # 眼睛：睁大
        "ParamEyeLOpen": 1.0,
        "ParamEyeROpen": 1.0,
        # 头部：后仰
        "ParamAngleX": -0.1,
        # 身体：前倾
        "ParamBodyAngleX": 0.1,
    },
}


class EmotionParamMapper(IEmotionParamMapper):
    """
    情绪参数映射器

    将情绪标签映射到 Live2D 模型参数。
    支持自定义映射配置。

    Attributes:
        mappings: 情绪到参数的映射字典
        default_duration: 默认过渡时长（秒）

    Example:
        >>> mapper = EmotionParamMapper()
        >>> frame = mapper.map_emotion("happy", intensity=0.8)
        >>> for param in frame.parameters:
        ...     print(f"{param.name}: {param.value}")
    """

    def __init__(
        self,
        mappings: Optional[Dict[str, Dict[str, float]]] = None,
        default_duration: float = 0.3
    ):
        """
        初始化映射器

        Args:
            mappings: 自定义映射配置（默认使用 DEFAULT_EMOTION_MAPPINGS）
            default_duration: 默认过渡时长
        """
        self.mappings = mappings or DEFAULT_EMOTION_MAPPINGS
        self.default_duration = default_duration

    def map_emotion(
        self,
        emotion: str,
        intensity: float = 1.0,
        context: Optional[Dict[str, Any]] = None
    ) -> ExpressionFrame:
        """
        将情绪映射到 Live2D 参数

        Args:
            emotion: 情绪名称
            intensity: 强度（0.0 - 1.0）
            context: 上下文信息

        Returns:
            ExpressionFrame: 表情帧
        """
        emotion_lower = emotion.lower()

        if emotion_lower not in self.mappings:
            logger.warning(f"[EmotionParamMapper] 未知情绪: {emotion}，使用 neutral")
            emotion_lower = "neutral"

        param_config = self.mappings[emotion_lower]

        # 创建参数列表
        parameters = []
        for param_name, base_value in param_config.items():
            # 应用强度
            value = self.apply_intensity(base_value, intensity)

            # 添加随机扰动（避免机械感）
            value = self._add_variance(value, intensity)

            parameters.append(ParameterState(
                name=param_name,
                value=value,
                duration=self.default_duration
            ))

        return ExpressionFrame(
            parameters=parameters,
            intensity=intensity,
            timestamp=0.0
        )

    def map_emotions_timeline(
        self,
        emotions: List[Tuple[str, float, float, float]],
        duration: float
    ) -> List[ExpressionFrame]:
        """
        将情绪时间轴映射到表情帧序列

        Args:
            emotions: [(emotion, start_time, end_time, intensity), ...]
            duration: 总时长

        Returns:
            List[ExpressionFrame]: 表情帧序列
        """
        frames = []

        for emotion, start_time, end_time, intensity in emotions:
            frame = self.map_emotion(emotion, intensity)
            frame.timestamp = start_time

            # 更新参数的 duration 为片段时长
            for param in frame.parameters:
                param.duration = end_time - start_time

            frames.append(frame)

        # 按时间排序
        frames.sort(key=lambda f: f.timestamp)

        return frames

    def _add_variance(self, value: float, intensity: float) -> float:
        """
        添加随机扰动

        让表情更自然，避免机械感。

        Args:
            value: 基础值
            intensity: 强度

        Returns:
            float: 添加扰动后的值
        """
        import random

        # 扰动范围随强度减小
        variance = 0.05 * intensity

        if variance > 0:
            value += random.uniform(-variance, variance)

        # 限制在合理范围
        return max(-1.0, min(1.0, value))

    @property
    def name(self) -> str:
        return "emotion_param_mapper"

    def get_supported_emotions(self) -> List[str]:
        """获取支持的情绪列表"""
        return list(self.mappings.keys())

    def add_emotion_mapping(
        self,
        emotion: str,
        param_mappings: Dict[str, float]
    ):
        """
        添加或更新情绪映射

        Args:
            emotion: 情绪名称
            param_mappings: 参数映射字典
        """
        self.mappings[emotion.lower()] = param_mappings

    def load_from_yaml(self, yaml_path: str):
        """
        从 YAML 文件加载映射配置

        Args:
            yaml_path: YAML 文件路径
        """
        import yaml
        from pathlib import Path

        path = Path(yaml_path)
        if not path.exists():
            logger.error(f"[EmotionParamMapper] 配置文件不存在: {yaml_path}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if 'emotions' in config:
            self.mappings.update(config['emotions'])
            logger.info(f"[EmotionParamMapper] 从 {yaml_path} 加载了 {len(config['emotions'])} 个情绪映射")
