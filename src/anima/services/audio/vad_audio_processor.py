"""
VAD 音频处理器实现

基于 VAD 的语音活动检测和音频累积
"""

import time
import numpy as np
from typing import List, Optional, Any, Callable, Dict
from loguru import logger

from .processor import AudioProcessorInterface
from ..intelligence.vad import VADInterface


class VADAudioProcessor(AudioProcessorInterface):
    """
    VAD 音频处理器

    负责：
    - 接收音频数据流
    - 使用 VAD 进行语音活动检测
    - 累积有效语音片段
    - 触发 ASR 转录和 LLM 对话
    """

    def __init__(
        self,
        session_id: str,
        vad_engine: VADInterface,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable[[List[float]], Any]] = None,
        sample_rate: int = 16000,
        vad_timeout_seconds: float = 30.0,
    ):
        """
        初始化 VAD 音频处理器

        Args:
            session_id: 会话 ID
            vad_engine: VAD 引擎
            on_speech_start: 语音开始回调
            on_speech_end: 语音结束回调，参数为累积的音频数据
            sample_rate: 采样率
            vad_timeout_seconds: VAD 超时时间（秒）
        """
        self.session_id = session_id
        self.vad_engine = vad_engine
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.sample_rate = sample_rate
        self.vad_timeout_seconds = vad_timeout_seconds

        # 音频缓冲区
        self._audio_buffer: List[float] = []

        # VAD 状态追踪
        self._vad_active_start_time: Optional[float] = None
        self._vad_chunk_count = 0
        self._is_speaking = False
        self._last_speech_time: Optional[float] = None

        # 统计
        self._total_chunks = 0
        self._speech_chunks = 0
        
        # 强制超时机制
        self._first_audio_time: Optional[float] = None
        self._max_audio_duration = 30.0  # 最大音频时长（秒）

    async def process_chunk(self, audio_data: List[float]) -> None:
        """
        处理音频数据块

        Args:
            audio_data: 音频数据（float32 列表）
        """
        if not audio_data:
            return

        self._total_chunks += 1

        # 调试日志：每 500 个块输出一次
        if self._total_chunks % 500 == 0:
            logger.info(f"[{self.session_id}] [AudioProcessor] Audio chunks: {self._total_chunks}")
        
        # 音频时长进度日志：每 10 秒输出一次
        if self._is_speaking and self._first_audio_time and self._total_chunks % 333 == 0:  # 约 10 秒
            audio_duration = time.time() - self._first_audio_time
            logger.info(f"[{self.session_id}] [AudioProcessor] 音频时长: {audio_duration:.1f}s / {self._max_audio_duration:.1f}s")

        # 如果没有 VAD 引擎，直接累积
        if not self.vad_engine:
            self._audio_buffer.extend(audio_data)
            if self._total_chunks == 1:
                logger.warning(f"[{self.session_id}] No VAD engine, audio will accumulate until manual end")
            return

        # VAD 检测
        try:
            result = self.vad_engine.detect_speech(audio_data)
            current_time = time.time()

            # 处理 VAD 状态
            if result.state.value == 'ACTIVE':
                self._handle_vad_active(current_time, audio_data)
            elif result.state.value == 'IDLE':
                self._handle_vad_idle(current_time)

            # 处理 VAD 事件
            if result.is_speech_start:
                await self._handle_speech_start()

            if result.is_speech_end and len(self._audio_buffer) > 1024:
                await self._handle_speech_end()
            
            # 强制超时检查：不管 VAD 状态如何，超过最大时长就结束
            if self._is_speaking and self._first_audio_time:
                audio_duration = current_time - self._first_audio_time
                if audio_duration > self._max_audio_duration:
                    logger.warning(f"[{self.session_id}] 强制超时 ({audio_duration:.1f}s)，结束语音")
                    await self._handle_speech_end()

        except Exception as e:
            logger.error(f"[{self.session_id}] VAD error: {e}", exc_info=True)

    async def process_end(self) -> None:
        """处理音频输入结束"""
        if not self._audio_buffer:
            logger.warning(f"[{self.session_id}] No audio data to process")
            return

        audio_duration = len(self._audio_buffer) / self.sample_rate
        logger.info(f"[{self.session_id}] Audio end: {audio_duration:.2f}s, {len(self._audio_buffer)} samples")

        # 触发语音结束
        await self._handle_speech_end()

    def reset(self) -> None:
        """重置处理器状态"""
        self._audio_buffer.clear()
        self._vad_active_start_time = None
        self._vad_chunk_count = 0
        self._is_speaking = False
        self._last_speech_time = None
        logger.debug(f"[{self.session_id}] Audio processor reset")

    def is_speaking(self) -> bool:
        """是否正在检测到语音"""
        return self._is_speaking

    # ========================================
    # 内部方法
    # ========================================

    def _handle_vad_active(self, current_time: float, audio_data: List[float]) -> None:
        """处理 VAD 活跃状态"""
        if self._vad_active_start_time is None:
            self._vad_active_start_time = current_time
            self._vad_chunk_count = 0
        
        # 记录首次音频时间
        if self._first_audio_time is None:
            self._first_audio_time = current_time

        self._vad_chunk_count += 1
        self._is_speaking = True
        self._last_speech_time = current_time

        # 累积音频数据
        self._audio_buffer.extend(audio_data)

        # 检查超时
        active_duration = current_time - self._vad_active_start_time
        if active_duration > self.vad_timeout_seconds:
            logger.warning(
                f"[{self.session_id}] VAD active for {active_duration:.1f}s, "
                f"exceeds timeout {self.vad_timeout_seconds}s"
            )
            # 强制结束
            self._vad_active_start_time = None

    def _handle_vad_idle(self, current_time: float) -> None:
        """处理 VAD 空闲状态"""
        # 检查是否需要清除状态
        if self._vad_active_start_time is not None:
            idle_duration = current_time - self._last_speech_time if self._last_speech_time else 0

            # 超过静音阈值，清除 VAD 活跃状态
            if idle_duration > 2.0:  # 2秒静音后清除
                self._clear_vad_state()

    def _clear_vad_state(self) -> None:
        """清除 VAD 活跃状态"""
        if self._vad_active_start_time is not None:
            logger.debug(f"[{self.session_id}] Clearing VAD active state after {self._vad_chunk_count} chunks")
            self._vad_active_start_time = None
            self._vad_chunk_count = 0

    async def _handle_speech_start(self) -> None:
        """处理语音开始"""
        if self._is_speaking:
            return

        self._is_speaking = True
        self._speech_chunks += 1

        logger.info(f"[{self.session_id}] 🎤 Speech started (chunk #{self._speech_chunks})")

        if self.on_speech_start:
            try:
                await self.on_speech_start()
            except Exception as e:
                logger.error(f"[{self.session_id}] Error in speech_start callback: {e}")

    async def _handle_speech_end(self, audio_data: Optional[List[float]] = None) -> None:
        """处理语音结束"""
        if not self._is_speaking:
            return

        # 使用累积的音频数据
        if audio_data is None:
            audio_data = list(self._audio_buffer)

        audio_duration = len(audio_data) / self.sample_rate

        logger.info(
            f"[{self.session_id}] 🎤 Speech ended: "
            f"{audio_duration:.2f}s, {len(audio_data)} samples, "
            f"{self._total_chunks} total chunks"
        )

        self._is_speaking = False
        self._first_audio_time = None  # 重置首次音频时间
        self._clear_vad_state()

        # 触发回调
        if self.on_speech_end:
            try:
                result = await self.on_speech_end(audio_data)
                logger.debug(f"[{self.session_id}] Speech end callback completed")
                return result
            except Exception as e:
                logger.error(f"[{self.session_id}] Error in speech_end callback: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_chunks": self._total_chunks,
            "speech_chunks": self._speech_chunks,
            "buffer_size": len(self._audio_buffer),
            "is_speaking": self._is_speaking,
            "buffer_duration": len(self._audio_buffer) / self.sample_rate if self._audio_buffer else 0,
        }
