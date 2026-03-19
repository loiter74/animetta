"""
统一事件处理器（增强版）

整合情绪分析、时间轴计算、参数映射和音频处理。
使用新的 IEmotionAnalyzer、ITimelineStrategy 和 IEmotionParamMapper 接口。

event.data 格式: dict
    - audio_path: str (必需) - 音频文件路径
    - text: str (可选) - 文本内容
    - emotions: list (可选) - 预计算的情绪列表
"""

import base64
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Union
from loguru import logger

from .base import BaseHandler
from anima.avatar.analyzers.base import IEmotionAnalyzer, EmotionData
from anima.avatar.strategies.base import ITimelineStrategy, TimelineSegment
from anima.avatar.mappers.base import IEmotionParamMapper, ExpressionFrame
from anima.avatar.mappers.emotion_param_mapper import EmotionParamMapper
from anima.avatar.analyzers.audio import AudioAnalyzer
from anima.avatar.factory import (
    create_emotion_analyzer,
    create_timeline_strategy
)

if TYPE_CHECKING:
    from anima.core import OutputEvent


class UnifiedEventHandler(BaseHandler):
    """
    统一事件处理器

    整合情绪分析、时间轴计算、参数映射和音频处理功能。
    处理 audio_with_expression 事件。

    event.data 格式:
        - audio_path: str (必需) - 音频文件路径
        - text: str (可选) - 文本内容
        - emotions: list (可选) - 预计算的情绪列表

    event.metadata 格式:
        - seq: int (可选) - 序号
    """

    # 必需的 data 键
    REQUIRED_DATA_KEYS = ["audio_path"]

    def __init__(
        self,
        websocket_send=None,
        analyzer_type: str = "llm_tag_analyzer",
        analyzer_config: Optional[Dict[str, Any]] = None,
        strategy_type: str = "position_based",
        strategy_config: Optional[Dict[str, Any]] = None,
        mapper_type: str = "emotion_param_mapper",
        mapper_config: Optional[Dict[str, Any]] = None,
        sample_rate: int = 50,
        use_parameter_mapping: bool = True
    ):
        """
        初始化处理器

        Args:
            websocket_send: WebSocket 发送函数
            analyzer_type: 情绪分析器类型
            analyzer_config: 情绪分析器配置
            strategy_type: 时间轴策略类型
            strategy_config: 时间轴策略配置
            mapper_type: 参数映射器类型
            mapper_config: 参数映射器配置
            sample_rate: 音量包络采样率（Hz）
            use_parameter_mapping: 是否使用参数映射（默认 True）
        """
        super().__init__(websocket_send)

        # 创建情绪分析器
        try:
            self.analyzer = create_emotion_analyzer(
                analyzer_type,
                config=analyzer_config or {}
            )
            logger.info(f"[{self.name}] 使用情绪分析器: {self.analyzer.name}")
        except Exception as e:
            logger.error(f"[{self.name}] 创建情绪分析器失败: {e}")
            raise

        # 创建时间轴策略
        try:
            self.strategy = create_timeline_strategy(
                strategy_type,
                config=strategy_config or {}
            )
            logger.info(f"[{self.name}] 使用时间轴策略: {self.strategy.name}")
        except Exception as e:
            logger.error(f"[{self.name}] 创建时间轴策略失败: {e}")
            raise

        # 创建参数映射器
        self.use_parameter_mapping = use_parameter_mapping
        if use_parameter_mapping:
            try:
                self.param_mapper = EmotionParamMapper(
                    mappings=mapper_config.get("mappings") if mapper_config else None,
                    default_duration=mapper_config.get("default_duration", 0.3) if mapper_config else 0.3
                )
                logger.info(f"[{self.name}] 使用参数映射器: {self.param_mapper.name}")
                logger.info(f"[{self.name}] 支持的情绪: {self.param_mapper.get_supported_emotions()}")
            except Exception as e:
                logger.error(f"[{self.name}] 创建参数映射器失败: {e}")
                raise
        else:
            self.param_mapper = None

        # 创建音频分析器
        self.audio_analyzer = AudioAnalyzer(sample_rate=sample_rate)
        self._sample_rate = sample_rate

    async def handle(self, event: "OutputEvent") -> None:
        """
        处理音频 + 表情事件
        """
        # 使用统一的提取方法
        data, metadata = self.extract_dict_data(
            event,
            required_keys=self.REQUIRED_DATA_KEYS,
        )

        if data is None:
            return

        # 提取字段
        audio_path = data["audio_path"]
        text = data.get("text", "")
        provided_emotions = data.get("emotions")
        seq = metadata.get("seq", event.seq) if isinstance(metadata, dict) else event.seq

        # 记录开始时间
        start_time = time.time()

        logger.info(
            f"[{self.name}] 开始处理 audio_with_expression 事件 (seq: {seq})"
        )

        if not audio_path:
            logger.warning(f"[{self.name}] 缺少 audio_path")
            return

        try:
            # 1. 读取音频文件
            audio_base64 = self._read_audio_as_base64(audio_path)
            audio_format = Path(audio_path).suffix.lstrip('.')

            logger.debug(f"[{self.name}] 音频读取完成 (格式: {audio_format})")

            # 2. 获取音频时长
            duration = self.audio_analyzer.get_audio_duration(audio_path)
            logger.debug(f"[{self.name}] 音频时长: {duration:.2f}s")

            # 3. 提取或使用提供的情绪
            extract_start = time.time()
            if provided_emotions:
                # 标准化为字符串列表
                emotions = self._normalize_emotions(provided_emotions)
                logger.debug(f"[{self.name}] 使用提供的情绪: {emotions}")
            else:
                emotion_data = self.analyzer.extract(text)
                emotions = self._extract_emotion_list(emotion_data)
                logger.debug(
                    f"[{self.name}] 情绪提取完成: {emotions} "
                    f"(分析器: {self.analyzer.name}, "
                    f"置信度: {emotion_data.confidence:.2f}, "
                    f"耗时: {(time.time() - extract_start)*1000:.1f}ms)"
                )

            # 4. 计算表情时间轴
            timeline_start = time.time()
            timeline_segments = self.strategy.calculate(
                emotions=emotions,
                text=text,
                audio_duration=duration
            )
            logger.debug(
                f"[{self.name}] 时间轴计算完成: {len(timeline_segments)} 个片段 "
                f"(策略: {self.strategy.name}, "
                f"耗时: {(time.time() - timeline_start)*1000:.1f}ms)"
            )

            # 5. 计算音量包络
            volume_start = time.time()
            volumes = self.audio_analyzer.compute_volume_envelope(audio_path)
            logger.debug(
                f"[{self.name}] 音量计算完成: {len(volumes)} 个采样 "
                f"(耗时: {(time.time() - volume_start)*1000:.1f}ms)"
            )

            # 6. 构建表情数据
            if self.use_parameter_mapping and self.param_mapper:
                # 使用参数映射：生成参数帧序列
                expressions_data = self._build_parameter_frames(timeline_segments, duration)
            else:
                # 传统模式：只发送表情名
                expressions_data = self._build_expressions_data(timeline_segments, duration)

            # 7. 发送统一消息
            await self.send({
                "type": "audio_with_expression",
                "audio_data": audio_base64,
                "format": audio_format,
                "volumes": volumes,
                "expressions": expressions_data,
                "text": text,
                "seq": seq,
                "use_parameter_mapping": self.use_parameter_mapping,
            })

            total_time = time.time() - start_time

            logger.info(
                f"[{self.name}] 事件处理成功 (seq: {seq}) "
                f"- 总耗时: {total_time*1000:.1f}ms, "
                f"音频: {duration:.2f}s, "
                f"片段: {len(timeline_segments)}, "
                f"模式: {'参数映射' if self.use_parameter_mapping else '传统表情'}"
            )

        except Exception as e:
            logger.error(
                f"[{self.name}] 处理失败 (seq: {seq}): {e}",
                exc_info=True
            )
            # 发送错误到前端
            await self.send({
                "type": "error",
                "message": f"音频处理失败: {str(e)}",
                "seq": seq
            })

    def _normalize_emotions(self, emotions: List[Union[str, Dict[str, Any]]]) -> List[str]:
        """
        标准化情绪列表为字符串列表

        支持两种格式：
        - 字符串: ["happy", "sad"]
        - 字典: [{"emotion": "happy", "position": 3}, ...]

        Args:
            emotions: 情绪列表（可能是字符串或字典）

        Returns:
            List[str]: 标准化后的情绪字符串列表
        """
        normalized = []

        for item in emotions:
            if isinstance(item, str):
                normalized.append(item)
            elif isinstance(item, dict):
                # 从字典中提取 emotion 字段
                emotion = item.get("emotion")
                if emotion:
                    normalized.append(emotion)
                else:
                    logger.warning(f"[{self.name}] 情绪字典缺少 'emotion' 字段: {item}")
            else:
                logger.warning(f"[{self.name}] 未知情绪类型: {type(item)}")

        return normalized if normalized else ["neutral"]

    def _extract_emotion_list(self, emotion_data: EmotionData) -> List[str]:
        """
        从 EmotionData 中提取情绪列表

        Args:
            emotion_data: 情绪数据

        Returns:
            List[str]: 情绪列表
        """
        # 如果有时间轴，从时间轴提取情绪
        if emotion_data.timeline:
            return [item.get("emotion", item) if isinstance(item, dict) else item
                    for item in emotion_data.timeline]

        # 否则，返回只包含主要情绪的列表
        return [emotion_data.primary] if emotion_data.primary else ["neutral"]

    def _build_expressions_data(
        self,
        segments: List[TimelineSegment],
        total_duration: float
    ) -> Dict[str, Any]:
        """
        构建表情时间轴数据（传统模式）

        Args:
            segments: TimelineSegment 列表
            total_duration: 总时长

        Returns:
            Dict: 表情数据（包含 intensity）
        """
        return {
            "segments": [
                seg.to_frontend_format()
                for seg in segments
            ],
            "total_duration": total_duration
        }

    def _build_parameter_frames(
        self,
        segments: List[TimelineSegment],
        total_duration: float
    ) -> Dict[str, Any]:
        """
        构建参数帧序列（参数映射模式）

        Args:
            segments: TimelineSegment 列表
            total_duration: 总时长

        Returns:
            Dict: 参数帧数据
        """
        frames = []

        for segment in segments:
            # 确保 segment.emotion 是字符串
            emotion = segment.emotion
            if isinstance(emotion, dict):
                emotion = emotion.get("emotion", "neutral")

            # 使用参数映射器将情绪转换为参数帧
            frame = self.param_mapper.map_emotion(
                emotion=str(emotion),
                intensity=segment.intensity
            )

            # 更新时间信息
            frame.timestamp = segment.start_time

            # 更新每个参数的 duration
            for param in frame.parameters:
                param.duration = segment.duration

            frames.append({
                "timestamp": frame.timestamp,
                "duration": segment.duration,
                "parameters": [p.to_dict() for p in frame.parameters],
                "intensity": frame.intensity
            })

        return {
            "frames": frames,
            "total_duration": total_duration
        }

    def _read_audio_as_base64(self, audio_path: str) -> str:
        """
        读取音频文件并转换为 base64

        Args:
            audio_path: 音频文件路径

        Returns:
            base64 编码的音频数据
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        with open(audio_path, 'rb') as f:
            audio_data = f.read()

        return base64.b64encode(audio_data).decode('utf-8')

    @property
    def name(self) -> str:
        """处理器名称"""
        return "unified_event_handler"

    def get_config_info(self) -> Dict[str, Any]:
        """
        获取处理器配置信息

        Returns:
            Dict: 配置信息
        """
        return {
            "analyzer": self.analyzer.name,
            "strategy": self.strategy.name,
            "mapper": self.param_mapper.name if self.param_mapper else None,
            "sample_rate": self._sample_rate,
            "use_parameter_mapping": self.use_parameter_mapping
        }
