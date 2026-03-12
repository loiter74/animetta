"""
Desktop Live2D Chatter - 桌面 Live2D 聊天适配器

处理来自 Electron 桌面应用的 WebSocket 连接，支持：
- 文本输入
- 语音输入（带 VAD 检测）
- Live2D 表情输出
- 音频输出

EventBus 架构：
- 输入：Adapter → EventBus.emit(INPUT_TEXT/INPUT_AUDIO) → InputHandler → Orchestrator
- 输出：Orchestrator → EventBus → Adapter.send() → 客户端
"""

import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass
from loguru import logger
import numpy as np

from ..base import ChannelAdapter, AdapterCapabilities
from anima.state import AudioBufferManager

if TYPE_CHECKING:
    from anima.events import EventBus, OutputEvent
    from anima.services.vad import VADInterface


@dataclass
class DesktopChatterConfig:
    """Desktop Live2D Chatter 配置"""
    # 音频参数
    sample_rate: int = 16000         # 采样率
    channels: int = 1                # 声道数

    # VAD 参数
    vad_enabled: bool = True         # 是否启用 VAD
    vad_timeout_seconds: float = 30.0  # VAD 超时时间

    # 自动打断
    auto_interrupt: bool = True      # 检测到新语音时自动打断


class DesktopLive2DChatter(ChannelAdapter):
    """
    桌面 Live2D 聊天适配器

    遵循 EventBus 架构：
    - 只依赖 EventBus，不直接依赖 Orchestrator
    - 输入通过 EventBus.emit(INPUT_TEXT/INPUT_AUDIO) 发送
    - 输出通过订阅 EventBus 接收

    使用示例:
        adapter = DesktopLive2DChatter(
            event_bus=event_bus,
            channel_id=sid,
            vad_engine=vad_engine,
            send_callback=lambda data: sio.emit(data['type'], data, to=sid),
        )

        await adapter.start()

        # 处理文本输入（通过 EventBus）
        await adapter.send_text("你好")

        # 处理音频数据
        await adapter.handle_audio_chunk(audio_data)

        # 处理音频结束
        await adapter.handle_audio_end()

        # 停止
        await adapter.stop()
    """

    # 类变量：共享的音频缓冲区管理器
    _audio_buffer_manager = AudioBufferManager()

    def __init__(
        self,
        event_bus: "EventBus",
        channel_id: str,
        vad_engine: Optional["VADInterface"] = None,
        config: Optional[DesktopChatterConfig] = None,
        send_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        session_id: Optional[str] = None,
    ):
        """
        初始化 Desktop Live2D Chatter

        Args:
            event_bus: 事件总线实例
            channel_id: 通道 ID（通常是 Socket.IO 的 sid）
            vad_engine: VAD 引擎（可选）
            config: 配置
            send_callback: 发送数据到客户端的回调函数
            session_id: 会话 ID（可选）
        """
        super().__init__(event_bus, channel_id, session_id)
        self.vad_engine = vad_engine
        self.config = config or DesktopChatterConfig()
        self._send_callback = send_callback

        # VAD 状态追踪
        self._vad_active_start_time: Optional[float] = None
        self._vad_chunk_count = 0
        self._audio_chunk_counter = 0

        # 状态
        self._is_speaking = False

    @property
    def channel_type(self) -> str:
        return "desktop_live2d"

    @property
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            text_input=True,
            voice_input=self.vad_engine is not None,
            image_input=False,
            text_output=True,
            audio_output=True,
            streaming=True,
            interrupt=True,
            vad=self.vad_engine is not None,
        )

    async def start(self) -> None:
        """启动适配器"""
        self._subscribe_output()
        self._is_running = True
        logger.info(f"[DesktopLive2DChatter] Started: channel_id={self.channel_id}")

    async def stop(self) -> None:
        """停止适配器"""
        self._unsubscribe_output()
        self._is_running = False
        self._clear_vad_state()
        # 清理共享缓冲区中的当前会话数据
        self._audio_buffer_manager.clear(self.session_id)
        logger.info(f"[DesktopLive2DChatter] Stopped: channel_id={self.channel_id}")

    async def send(self, event: "OutputEvent") -> None:
        """
        发送输出事件到客户端

        将事件转换为前端格式并发送
        """
        if not self._send_callback:
            return

        try:
            event_type = event.type

            # 根据事件类型转换格式
            if event_type == "sentence":
                await self._send_text_output(event)
            elif event_type in ("audio", "audio_with_expression"):
                await self._send_audio_output(event)
            elif event_type == "control":
                await self._send_control(event)
            else:
                # 其他事件直接转发
                await self._send_callback({
                    "type": event_type,
                    "data": event.data,
                    "seq": event.seq,
                })

        except Exception as e:
            logger.error(f"[DesktopLive2DChatter] Error sending event: {e}")

    # === 输入处理 API（通过 EventBus）===

    async def send_text(
        self,
        text: str,
        user_id: Optional[str] = None,
        user_name: str = "User",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        发送文本输入（通过 EventBus）

        Args:
            text: 用户输入的文本
            user_id: 用户 ID（可选）
            user_name: 发送者名称
            metadata: 额外元数据
        """
        if not self._is_running:
            logger.warning("[DesktopLive2DChatter] Adapter not running")
            return

        if not text or not text.strip():
            return

        logger.info(f"[{self.channel_id}] Text input: {text[:50]}...")

        # 通过 EventBus 发送 INPUT_TEXT 事件
        await self._emit_input(
            event_type="INPUT_TEXT",
            content=text.strip(),
            user_id=user_id,
            user_name=user_name,
            metadata={
                **(metadata or {}),
                "sample_rate": self.config.sample_rate,
            },
        )

    async def send_audio(
        self,
        audio_data: List[float],
        user_id: Optional[str] = None,
        user_name: str = "User",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        发送音频输入（通过 EventBus）

        Args:
            audio_data: 音频数据（float32 列表）
            user_id: 用户 ID（可选）
            user_name: 发送者名称
            metadata: 额外元数据
        """
        if not self._is_running:
            return

        if not audio_data:
            return

        logger.info(f"[{self.channel_id}] Sending audio input: {len(audio_data)} samples")

        # 通过 EventBus 发送 INPUT_AUDIO 事件
        await self._emit_input(
            event_type="INPUT_AUDIO",
            content=audio_data,
            user_id=user_id,
            user_name=user_name,
            metadata={
                **(metadata or {}),
                "sample_rate": self.config.sample_rate,
            },
        )

    async def send_interrupt(self, heard_text: str = "") -> None:
        """
        发送打断信号（通过 EventBus）

        Args:
            heard_text: 用户已听到的部分文本
        """
        logger.info(f"[{self.channel_id}] Interrupt signal, heard: {heard_text[:50] if heard_text else '(empty)'}")

        # 通过 EventBus 发送 INTERRUPT 事件
        from anima.events import OutputEvent

        event = OutputEvent(
            type="INTERRUPT",
            data={
                "heard_text": heard_text,
                "channel_id": self.channel_id,
            },
            metadata={
                "channel_id": self.channel_id,
                "session_id": self.session_id,
            },
        )

        await self.event_bus.emit(event)

        # 清空音频缓冲区
        self._audio_buffer_manager.clear(self.session_id)
        self._clear_vad_state()

    # === 兼容性 API（保持向后兼容）===

    async def handle_text_input(
        self,
        text: str,
        from_name: str = "User",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        处理文本输入（兼容旧 API）

        Args:
            text: 用户输入的文本
            from_name: 发送者名称
            metadata: 额外元数据
        """
        await self.send_text(
            text=text,
            user_name=from_name,
            metadata=metadata,
        )

    async def handle_audio_chunk(self, audio_data: List[float]) -> None:
        """
        处理音频数据块（带 VAD 检测）

        Args:
            audio_data: 音频数据（float32 列表）
        """
        if not self._is_running:
            return

        if not audio_data:
            return

        self._audio_chunk_counter += 1

        # 没有 VAD，直接累积
        if not self.vad_engine:
            self._audio_buffer_manager.append(self.session_id, audio_data)
            if self._audio_chunk_counter % 100 == 1:
                logger.warning(f"[{self.channel_id}] No VAD, accumulating audio directly")
            return

        # VAD 检测
        try:
            result = self.vad_engine.detect_speech(audio_data)

            # VAD 超时保护
            current_time = time.time()

            if result.state.value == 'ACTIVE':
                self._handle_vad_active(current_time)
            elif result.state.value == 'IDLE':
                self._clear_vad_state()

            # 处理 VAD 事件
            if result.is_speech_start:
                await self._handle_speech_start()

            if result.is_speech_end and len(result.audio_data) > 1024:
                await self._handle_speech_end(result.audio_data)

        except Exception as e:
            logger.error(f"[{self.channel_id}] VAD error: {e}", exc_info=True)

    async def handle_audio_end(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        from_name: str = "User",
    ) -> None:
        """
        处理音频输入结束

        将累积的音频通过 EventBus 发送
        """
        if not self._is_running:
            return

        # 获取累积的音频
        audio_data = self._audio_buffer_manager.pop(self.session_id)

        if audio_data is None or len(audio_data) == 0:
            logger.warning(f"[{self.channel_id}] No audio data")
            await self._send_control_signal("no-audio-data")
            return

        audio_duration = len(audio_data) / self.config.sample_rate
        logger.info(f"[{self.channel_id}] Audio end: {audio_duration:.2f}s")

        # 通过 EventBus 发送 INPUT_AUDIO 事件
        await self.send_audio(
            audio_data=audio_data.tolist() if hasattr(audio_data, 'tolist') else list(audio_data),
            user_name=from_name,
            metadata=metadata,
        )

    async def handle_interrupt(self, heard_text: str = "") -> None:
        """
        处理打断信号（兼容旧 API）

        Args:
            heard_text: 用户已听到的部分文本
        """
        await self.send_interrupt(heard_text=heard_text)

    # === VAD 辅助方法 ===

    def _handle_vad_active(self, current_time: float) -> None:
        """处理 VAD 活跃状态"""
        if self._vad_active_start_time is None:
            self._vad_active_start_time = current_time
            self._vad_chunk_count = 0

        self._vad_chunk_count += 1

        # 检查超时
        active_duration = current_time - self._vad_active_start_time
        if active_duration > self.config.vad_timeout_seconds:
            logger.warning(
                f"[{self.channel_id}] VAD active for {active_duration:.1f}s, "
                f"exceeds timeout {self.config.vad_timeout_seconds}s"
            )

    def _clear_vad_state(self) -> None:
        """清除 VAD 状态"""
        self._vad_active_start_time = None
        self._vad_chunk_count = 0

    async def _handle_speech_start(self) -> None:
        """处理语音开始事件"""
        logger.info(f"[{self.channel_id}] Speech start detected")

        # 自动打断（通过 EventBus 发送 INTERRUPT 事件）
        if self.config.auto_interrupt:
            logger.info(f"[{self.channel_id}] New speech detected, auto-interrupting")
            await self.send_interrupt()
            await self._send_control_signal("interrupt")

    async def _handle_speech_end(self, audio_data: bytes) -> None:
        """
        处理语音结束事件

        Args:
            audio_data: VAD 检测到的音频数据（int16 bytes）
        """
        logger.info(f"[{self.channel_id}] Speech end detected: {len(audio_data)} bytes")

        # 清除 VAD 状态
        self._clear_vad_state()

        # 转换音频格式
        audio_float = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32767.0
        self._audio_buffer_manager.append(self.session_id, audio_float.tolist())

        # 发送控制信号通知前端
        await self._send_control_signal("mic-audio-end")

        # 直接触发音频处理
        await self.handle_audio_end()

    # === 输出辅助方法 ===

    async def _send_text_output(self, event: "OutputEvent") -> None:
        """发送文本输出"""
        text = event.data
        # 防御性检查：确保 metadata 是 dict 类型
        metadata = event.metadata
        is_complete = False
        if isinstance(metadata, dict):
            is_complete = metadata.get("is_complete", False)

        await self._send_callback({
            "type": "sentence",
            "text": text if not is_complete else "",
            "seq": event.seq,
        })

    async def _send_audio_output(self, event: "OutputEvent") -> None:
        """发送音频输出"""
        await self._send_callback({
            "type": event.type,
            "data": event.data,
            "seq": event.seq,
        })

    async def _send_control(self, event: "OutputEvent") -> None:
        """发送控制信号"""
        signal = event.data.get("signal") if isinstance(event.data, dict) else None

        if signal == "conversation-start":
            self._is_speaking = True
        elif signal == "conversation-end":
            self._is_speaking = False

        await self._send_callback({
            "type": "control",
            "signal": signal,
            "data": event.data,
        })

    async def _send_control_signal(self, signal: str) -> None:
        """发送控制信号"""
        await self._send_callback({
            "type": "control",
            "text": signal,
        })

    async def _send_error(self, message: str) -> None:
        """发送错误消息"""
        await self._send_callback({
            "type": "error",
            "message": message,
        })

    # === 属性 ===

    @property
    def is_speaking(self) -> bool:
        """AI 是否正在说话"""
        return self._is_speaking

    @property
    def is_running(self) -> bool:
        """适配器是否运行中"""
        return self._is_running

    @property
    def audio_buffer_manager(self) -> AudioBufferManager:
        """获取音频缓冲区管理器（类变量）"""
        return self._audio_buffer_manager

