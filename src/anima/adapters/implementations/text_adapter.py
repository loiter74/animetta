"""
Text Input Adapter - 文本输入适配器

提供简单的文本输入能力，适用于：
- CLI 交互
- REST API
- 简单测试场景
"""

from typing import Any, Callable, Dict, Optional, TYPE_CHECKING
from loguru import logger

from ..base import ChannelAdapter, AdapterCapabilities

if TYPE_CHECKING:
    from anima.events import EventBus, OutputEvent


class TextInputAdapter(ChannelAdapter):
    """
    文本输入适配器

    简单的文本输入适配器，支持：
    - 接收文本输入并通过 EventBus 发送 INPUT_TEXT 事件
    - 接收输出事件并回调处理

    使用示例:
        # 创建适配器
        adapter = TextInputAdapter(
            event_bus=event_bus,
            channel_id="cli-001",
            on_output=lambda event: print(event.data)
        )

        # 启动
        await adapter.start()

        # 发送文本输入
        await adapter.send_text("你好")

        # 停止
        await adapter.stop()
    """

    def __init__(
        self,
        event_bus: "EventBus",
        channel_id: str,
        session_id: Optional[str] = None,
        on_output: Optional[Callable[["OutputEvent"], None]] = None,
    ):
        """
        初始化文本输入适配器

        Args:
            event_bus: 事件总线实例
            channel_id: 通道 ID
            session_id: 会话 ID（可选）
            on_output: 输出回调函数 (event) -> None
        """
        super().__init__(event_bus, channel_id, session_id)
        self._on_output = on_output

    @property
    def channel_type(self) -> str:
        return "text"

    @property
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            text_input=True,
            voice_input=False,
            image_input=False,
            text_output=True,
            audio_output=False,
            streaming=True,
            interrupt=True,
            vad=False,
        )

    async def start(self) -> None:
        """启动适配器"""
        self._subscribe_output()
        self._is_running = True
        logger.info(f"[TextInputAdapter] Started: channel_id={self.channel_id}")

    async def stop(self) -> None:
        """停止适配器"""
        self._unsubscribe_output()
        self._is_running = False
        logger.info(f"[TextInputAdapter] Stopped: channel_id={self.channel_id}")

    async def send(self, event: "OutputEvent") -> None:
        """
        发送输出事件到客户端

        调用回调函数处理输出事件
        """
        if self._on_output:
            try:
                self._on_output(event)
            except Exception as e:
                logger.error(f"[TextInputAdapter] Error in output callback: {e}")

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
            logger.warning(f"[TextInputAdapter] Adapter not running, ignoring input")
            return

        logger.debug(f"[TextInputAdapter] Sending text input: {text[:50]}...")

        await self._emit_input(
            event_type="INPUT_TEXT",
            content=text,
            user_id=user_id,
            user_name=user_name,
            metadata=metadata,
        )

    async def send_interrupt(self) -> None:
        """发送打断信号"""
        from anima.events import OutputEvent

        event = OutputEvent(
            type="INTERRUPT",
            data={
                "channel_id": self.channel_id,
            },
            metadata={
                "channel_id": self.channel_id,
                "session_id": self.session_id,
            },
        )

        await self.event_bus.emit(event)
        logger.debug(f"[TextInputAdapter] Sent interrupt signal")
