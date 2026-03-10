"""
Input Event Handler - 输入事件处理器

订阅 INPUT_TEXT/INPUT_AUDIO 事件并路由到 Orchestrator。

这是 EventBus 架构的一部分，负责将适配器发出的输入事件
转换为 Orchestrator 的处理请求。
"""

from typing import Dict, Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from anima.events import EventBus, OutputEvent
    from anima.services.conversation import ConversationOrchestrator
    from anima.services.asr import ASRInterface


class InputHandler:
    """
    输入事件处理器

    订阅 INPUT_TEXT 和 INPUT_AUDIO 事件，并路由到 Orchestrator。

    使用示例:
        handler = InputHandler(
            event_bus=event_bus,
            orchestrator_registry=get_orchestrator_registry,
            asr_service=asr_service,
        )

        await handler.start()

        # 现在所有 INPUT_TEXT/INPUT_AUDIO 事件都会被处理
    """

    def __init__(
        self,
        event_bus: "EventBus",
        orchestrator_registry: callable,
        asr_service: Optional["ASRInterface"] = None,
    ):
        """
        初始化输入事件处理器

        Args:
            event_bus: 事件总线实例
            orchestrator_registry: 获取 Orchestrator 的函数 (session_id) -> Orchestrator
            asr_service: ASR 服务（用于处理音频输入，可选）
        """
        self.event_bus = event_bus
        self.orchestrator_registry = orchestrator_registry
        self.asr_service = asr_service

        self._text_subscription = None
        self._audio_subscription = None
        self._is_running = False

    async def start(self) -> None:
        """启动处理器"""
        if self._is_running:
            return

        # 订阅输入事件
        self._text_subscription = self.event_bus.subscribe(
            "INPUT_TEXT",
            self._handle_text_input,
        )

        self._audio_subscription = self.event_bus.subscribe(
            "INPUT_AUDIO",
            self._handle_audio_input,
        )

        self._is_running = True
        logger.info("[InputHandler] Started")

    async def stop(self) -> None:
        """停止处理器"""
        if not self._is_running:
            return

        # 取消订阅
        if self._text_subscription:
            self.event_bus.unsubscribe(self._text_subscription)
            self._text_subscription = None

        if self._audio_subscription:
            self.event_bus.unsubscribe(self._audio_subscription)
            self._audio_subscription = None

        self._is_running = False
        logger.info("[InputHandler] Stopped")

    async def _handle_text_input(self, event: "OutputEvent") -> None:
        """
        处理文本输入事件

        Args:
            event: 输出事件（类型为 INPUT_TEXT）
        """
        try:
            # 提取事件数据
            data = event.data or {}
            content = data.get("content", "")
            user_id = data.get("user_id")
            user_name = data.get("user_name")

            # 提取元数据
            metadata = event.metadata or {}
            session_id = metadata.get("session_id")

            if not content:
                logger.warning("[InputHandler] Empty text input, ignoring")
                return

            # 获取对应的 Orchestrator
            orchestrator = self.orchestrator_registry(session_id)
            if not orchestrator:
                logger.warning(f"[InputHandler] No orchestrator found for session: {session_id}")
                return

            logger.debug(f"[InputHandler] Processing text input: session={session_id}, text={content[:50]}...")

            # 调用 Orchestrator 处理输入
            await orchestrator.process_input(
                text=content,
                user_id=user_id,
                user_name=user_name,
            )

        except Exception as e:
            logger.error(f"[InputHandler] Error handling text input: {e}", exc_info=True)

    async def _handle_audio_input(self, event: "OutputEvent") -> None:
        """
        处理音频输入事件

        Args:
            event: 输出事件（类型为 INPUT_AUDIO）
        """
        try:
            # 提取事件数据
            data = event.data or {}
            content = data.get("content")
            user_id = data.get("user_id")
            user_name = data.get("user_name")
            extra_metadata = data.get("metadata", {})

            # 提取元数据
            metadata = event.metadata or {}
            session_id = metadata.get("session_id")

            if not content:
                logger.warning("[InputHandler] Empty audio input, ignoring")
                return

            if not self.asr_service:
                logger.warning("[InputHandler] No ASR service configured, cannot process audio")
                return

            # 获取对应的 Orchestrator
            orchestrator = self.orchestrator_registry(session_id)
            if not orchestrator:
                logger.warning(f"[InputHandler] No orchestrator found for session: {session_id}")
                return

            # 获取采样率
            sample_rate = extra_metadata.get("sample_rate", 16000)

            # 标准化音频格式
            import numpy as np
            if isinstance(content, list):
                audio_data = np.array(content, dtype=np.float32)
            elif isinstance(content, np.ndarray):
                audio_data = content
            else:
                logger.warning(f"[InputHandler] Unsupported audio format: {type(content)}")
                return

            logger.debug(f"[InputHandler] Processing audio input: session={session_id}")

            # ASR 转写
            text = await self.asr_service.transcribe(audio_data, sample_rate=sample_rate)

            if not text or not text.strip():
                logger.debug("[InputHandler] ASR returned empty text")
                return

            logger.info(f"[InputHandler] ASR result: {text}")

            # 调用 Orchestrator 处理转写后的文本
            await orchestrator.process_input(
                text=text.strip(),
                user_id=user_id,
                user_name=user_name,
            )

        except Exception as e:
            logger.error(f"[InputHandler] Error handling audio input: {e}", exc_info=True)

    @property
    def is_running(self) -> bool:
        """处理器是否运行中"""
        return self._is_running
