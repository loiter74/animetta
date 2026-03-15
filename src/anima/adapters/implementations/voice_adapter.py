"""
Voice Input Adapter - 语音输入适配器

提供语音输入能力，支持：
- 接收音频数据并通过 ASR 转换为文本
- 接收文本输入
- 与后端 ASR/TTS 流程对接
"""

from typing import Any, Callable, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
from loguru import logger
import numpy as np

from ..base import ChannelAdapter, AdapterCapabilities

if TYPE_CHECKING:
    from anima.events import EventBus, OutputEvent
    from anima.services.asr import ASRInterface


@dataclass
class VoiceAdapterConfig:
    """语音适配器配置"""
    # 音频参数
    sample_rate: int = 16000         # 采样率
    channels: int = 1                # 声道数
    chunk_ms: int = 100              # 每个音频块的毫秒数

    # VAD 参数
    vad_enabled: bool = True         # 是否启用 VAD
    vad_silence_ms: int = 500        # 静音判定时间（毫秒）
    vad_threshold: float = 0.5       # VAD 概率阈值


class VoiceInputAdapter(ChannelAdapter):
    """
    语音输入适配器

    支持语音输入和文本输入的适配器，通常用于：
    - WebSocket 客户端
    - Electron 桌面应用
    - 实时语音对话场景

    使用示例:
        # 创建适配器
        adapter = VoiceInputAdapter(
            event_bus=event_bus,
            channel_id="voice-001",
            asr_service=asr_service,
            config=VoiceAdapterConfig(vad_enabled=True),
            on_output=lambda event: print(event),
            on_audio_output=lambda event: play_audio(event.data),
        )

        # 启动
        await adapter.start()

        # 发送音频数据
        await adapter.send_audio(audio_chunk)

        # 发送文本
        await adapter.send_text("你好")

        # 停止
        await adapter.stop()
    """

    def __init__(
        self,
        event_bus: "EventBus",
        channel_id: str,
        asr_service: Optional["ASRInterface"] = None,
        config: Optional[VoiceAdapterConfig] = None,
        session_id: Optional[str] = None,
        on_output: Optional[Callable[["OutputEvent"], None]] = None,
        on_audio_output: Optional[Callable[["OutputEvent"], None]] = None,
    ):
        """
        初始化语音输入适配器

        Args:
            event_bus: 事件总线实例
            channel_id: 通道 ID
            asr_service: ASR 服务（用于处理音频输入）
            config: 语音适配器配置
            session_id: 会话 ID（可选）
            on_output: 文本输出回调函数
            on_audio_output: 音频输出回调函数
        """
        super().__init__(event_bus, channel_id, session_id)
        self.asr_service = asr_service
        self.config = config or VoiceAdapterConfig()
        self._on_output = on_output
        self._on_audio_output = on_audio_output

        # 状态
        self._is_speaking = False

    @property
    def channel_type(self) -> str:
        return "voice"

    @property
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            text_input=True,
            voice_input=True,
            image_input=False,
            text_output=True,
            audio_output=True,
            streaming=True,
            interrupt=True,
            vad=self.config.vad_enabled,
        )

    async def start(self) -> None:
        """启动适配器"""
        self._subscribe_output()
        self._is_running = True
        self._is_speaking = False
        logger.info(f"[VoiceInputAdapter] Started: channel_id={self.channel_id}")

    async def stop(self) -> None:
        """停止适配器"""
        self._unsubscribe_output()
        self._is_running = False
        self._is_speaking = False
        logger.info(f"[VoiceInputAdapter] Stopped: channel_id={self.channel_id}")

    async def send(self, event: "OutputEvent") -> None:
        """
        发送输出事件到客户端

        根据事件类型调用不同的回调函数
        """
        try:
            event_type = event.type

            if event_type in ("audio", "audio_with_expression"):
                if self._on_audio_output:
                    self._on_audio_output(event)
            elif event_type == "sentence":
                if self._on_output:
                    self._on_output(event)
            elif event_type == "control":
                # 处理控制信号
                signal = event.data.get("signal") if isinstance(event.data, dict) else None
                if signal == "conversation-start":
                    self._is_speaking = True
                elif signal == "conversation-end":
                    self._is_speaking = False
                if self._on_output:
                    self._on_output(event)
            else:
                # 其他事件类型
                if self._on_output:
                    self._on_output(event)

        except Exception as e:
            logger.error(f"[VoiceInputAdapter] Error in output callback: {e}")

    # === 公共 API ===

    async def send_text(
        self,
        text: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        发送文本输入

        通过 EventBus 发送 INPUT_TEXT 事件

        Args:
            text: 用户输入的文本
            user_id: 用户 ID（可选）
            user_name: 用户显示名称（可选）
            metadata: 额外元数据（可选）
        """
        if not self._is_running:
            logger.warning(f"[VoiceInputAdapter] Adapter not running, ignoring input")
            return

        logger.debug(f"[VoiceInputAdapter] Sending text input: {text[:50]}...")

        await self._emit_input(
            event_type="INPUT_TEXT",
            content=text,
            user_id=user_id,
            user_name=user_name,
            metadata=metadata,
        )

    async def send_audio(
        self,
        audio_data: Any,
        sample_rate: Optional[int] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        发送音频输入

        通过 ASR 转换为文本，然后发送 INPUT_TEXT 事件

        Args:
            audio_data: 音频数据（可以是 list, bytes, 或 numpy array）
            sample_rate: 采样率（可选，默认使用配置值）
            user_id: 用户 ID（可选）
            user_name: 用户显示名称（可选）
            metadata: 额外元数据（可选）
        """
        if not self._is_running:
            logger.warning(f"[VoiceInputAdapter] Adapter not running, ignoring input")
            return

        if not self.asr_service:
            logger.warning(f"[VoiceInputAdapter] No ASR service configured")
            return

        # 标准化音频数据格式
        audio_array = self._normalize_audio(audio_data)
        if audio_array is None:
            return

        # 获取采样率
        actual_sample_rate = sample_rate or self.config.sample_rate

        logger.debug(f"[VoiceInputAdapter] Processing audio input: shape={audio_array.shape}")

        try:
            # ASR 转写
            text = await self.asr_service.transcribe(audio_array, sample_rate=actual_sample_rate)

            if not text or not text.strip():
                logger.debug(f"[VoiceInputAdapter] ASR returned empty text")
                return

            logger.info(f"[VoiceInputAdapter] ASR result: {text}")

            # 发送 transcript 事件到前端（显示用户语音输入）
            if self._send_callback:
                import json
                await self._send_callback(json.dumps({
                    "type": "user-transcript",
                    "text": text.strip()
                }))

            # 通过 EventBus 发送 INPUT_TEXT 事件
            await self._emit_input(
                event_type="INPUT_TEXT",
                content=text.strip(),
                user_id=user_id,
                user_name=user_name,
                metadata={
                    **(metadata or {}),
                    "source": "audio",
                    "sample_rate": actual_sample_rate,
                },
            )

        except Exception as e:
            logger.error(f"[VoiceInputAdapter] Error processing audio: {e}", exc_info=True)

    async def send_interrupt(self, heard_text: Optional[str] = None) -> None:
        """
        发送打断信号

        Args:
            heard_text: 用户已听到的部分文本（可选）
        """
        from anima.events import OutputEvent

        event = OutputEvent(
            type="INTERRUPT",
            data={
                "channel_id": self.channel_id,
                "heard_text": heard_text,
            },
            metadata={
                "channel_id": self.channel_id,
                "session_id": self.session_id,
            },
        )

        await self.event_bus.emit(event)
        logger.debug(f"[VoiceInputAdapter] Sent interrupt signal")

    # === 辅助方法 ===

    def _normalize_audio(self, audio_data: Any) -> Optional[np.ndarray]:
        """
        标准化音频数据格式

        将各种格式的音频数据转换为统一的 numpy array 格式
        """
        try:
            if isinstance(audio_data, np.ndarray):
                return audio_data.astype(np.float32)
            elif isinstance(audio_data, list):
                return np.array(audio_data, dtype=np.float32)
            elif isinstance(audio_data, bytes):
                # 假设是 int16 PCM
                arr = np.frombuffer(audio_data, dtype=np.int16)
                # 转换为 float32 归一化
                return (arr.astype(np.float32) / 32767.0)
            else:
                logger.warning(f"[VoiceInputAdapter] Unknown audio format: {type(audio_data)}")
                return None
        except Exception as e:
            logger.error(f"[VoiceInputAdapter] Error normalizing audio: {e}")
            return None

    # === 属性 ===

    @property
    def is_speaking(self) -> bool:
        """AI 是否正在说话"""
        return self._is_speaking

    @property
    def is_running(self) -> bool:
        """适配器是否运行中"""
        return self._is_running
