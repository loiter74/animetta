"""
Adapter Base Classes - 适配器基类

定义通道适配器的核心接口。

设计原则：
1. Adapter 只依赖 EventBus，不依赖 Orchestrator
2. 输入：Adapter → EventBus.emit(INPUT_TEXT/INPUT_AUDIO)
3. 输出：EventBus → Adapter.send() → 客户端
4. Adapter 只负责"转换"和"传输"，不负责业务逻辑
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from anima.events import EventBus, OutputEvent


@dataclass
class AdapterCapabilities:
    """
    适配器能力声明

    描述该适配器支持的输入/输出类型
    """
    # 输入能力
    text_input: bool = True          # 支持文本输入
    voice_input: bool = False        # 支持语音输入
    image_input: bool = False        # 支持图片输入

    # 输出能力
    text_output: bool = True         # 支持文本输出
    audio_output: bool = False       # 支持音频输出

    # 流式能力
    streaming: bool = False          # 支持流式响应

    # 其他能力
    interrupt: bool = False          # 支持打断
    vad: bool = False                # 支持语音活动检测


class ChannelAdapter(ABC):
    """
    通道适配器基类

    所有通道适配器（Socket.IO、REST、CLI 等）都应继承此类。

    职责：
    1. 接收外部输入 → EventBus.emit(INPUT_TEXT/INPUT_AUDIO)
    2. 订阅输出事件 → 发送给外部客户端

    使用示例:
        class SocketIOAdapter(ChannelAdapter):
            @property
            def channel_type(self) -> str:
                return "socketio"

            async def start(self) -> None:
                self._subscribe_output()
                # 注册 Socket.IO 事件处理器...

            async def stop(self) -> None:
                self._unsubscribe_output()

            async def send(self, event: OutputEvent) -> None:
                await self._sio.emit(event.type, event.to_dict(), to=self._sid)
    """

    def __init__(
        self,
        event_bus: "EventBus",
        channel_id: str,
        session_id: Optional[str] = None,
    ):
        """
        初始化适配器

        Args:
            event_bus: 事件总线实例
            channel_id: 通道实例 ID（唯一标识一个连接）
            session_id: 会话 ID（可选，默认与 channel_id 相同）
        """
        self.event_bus = event_bus
        self.channel_id = channel_id
        self.session_id = session_id or channel_id
        self._output_subscription = None
        self._is_running = False

        logger.debug(f"[{self.channel_type}] Adapter created: channel_id={channel_id}")

    @property
    def is_running(self) -> bool:
        """适配器是否运行中"""
        return self._is_running

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """
        通道类型标识

        Returns:
            str: 如 "socketio", "rest", "cli", "discord"
        """
        pass

    @property
    def capabilities(self) -> AdapterCapabilities:
        """
        适配器能力

        子类可以覆盖此属性来声明自己的能力
        """
        return AdapterCapabilities()

    @abstractmethod
    async def start(self) -> None:
        """
        启动适配器

        包括：
        - 订阅 EventBus 输出事件
        - 启动外部连接监听
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """
        停止适配器

        包括：
        - 取消 EventBus 订阅
        - 关闭外部连接
        """
        pass

    @abstractmethod
    async def send(self, event: "OutputEvent") -> None:
        """
        发送输出事件到客户端

        将事件转换为客户端格式并发送

        Args:
            event: 输出事件
        """
        pass

    # === 辅助方法 ===

    def _subscribe_output(self) -> None:
        """订阅输出事件"""
        self._output_subscription = self.event_bus.subscribe_all(
            self._handle_output_event
        )
        logger.debug(f"[{self.channel_type}] Subscribed to output events")

    def _unsubscribe_output(self) -> None:
        """取消订阅输出事件"""
        if self._output_subscription:
            self.event_bus.unsubscribe(self._output_subscription)
            self._output_subscription = None
            logger.debug(f"[{self.channel_type}] Unsubscribed from output events")

    async def _handle_output_event(self, event: "OutputEvent") -> None:
        """
        处理输出事件（内部方法）

        过滤只处理当前会话的事件，然后调用 send()
        """
        # 检查是否是当前会话的事件
        metadata = event.metadata or {}
        event_session_id = metadata.get("session_id")

        # 如果事件没有 session_id 或者 session_id 匹配，则处理
        if event_session_id is None or event_session_id == self.session_id:
            try:
                await self.send(event)
            except Exception as e:
                logger.error(f"[{self.channel_type}] Error sending event: {e}")

    async def _emit_input(
        self,
        event_type: str,
        content: Any,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        发送输入事件到 EventBus

        Args:
            event_type: 事件类型 (INPUT_TEXT / INPUT_AUDIO / INPUT_IMAGE)
            content: 消息内容
            user_id: 用户 ID（可选）
            user_name: 用户显示名称（可选）
            metadata: 额外元数据（可选）
        """
        from anima.events import OutputEvent

        event = OutputEvent(
            type=event_type,
            data={
                "content": content,
                "user_id": user_id,
                "user_name": user_name,
                "metadata": metadata or {},
            },
            metadata={
                "channel_id": self.channel_id,
                "channel_type": self.channel_type,
                "session_id": self.session_id,
            },
        )

        await self.event_bus.emit(event)
        logger.debug(f"[{self.channel_type}] Emitted {event_type} event")


class InputAdapter(ABC):
    """
    输入适配器接口

    专门处理输入转换的适配器。对于只需要处理输入的场景（如 CLI），
    可以只实现 InputAdapter 而不实现完整的 ChannelAdapter。

    这个接口更轻量，适合：
    - 只需要单向输入的场景
    - 测试和调试
    - 简单的集成场景
    """

    @abstractmethod
    async def receive_text(self, text: str, **kwargs) -> None:
        """
        接收文本输入

        Args:
            text: 用户输入的文本
            **kwargs: 额外参数（user_id, metadata 等）
        """
        pass

    @abstractmethod
    async def receive_audio(self, audio_data: bytes, **kwargs) -> None:
        """
        接收音频输入

        Args:
            audio_data: 音频数据（通常是 PCM 或 WAV 格式）
            **kwargs: 额外参数（sample_rate, user_id 等）
        """
        pass


class OutputAdapter(ABC):
    """
    输出适配器接口

    专门处理输出转换的适配器。对于只需要处理输出的场景，
    可以只实现 OutputAdapter。

    这个接口适合：
    - 只需要接收响应的场景
    - 被动接收的客户端
    """

    @abstractmethod
    async def send_text(self, text: str, **kwargs) -> None:
        """
        发送文本输出

        Args:
            text: AI 回复的文本
            **kwargs: 额外参数（seq, is_final 等）
        """
        pass

    @abstractmethod
    async def send_audio(self, audio_data: bytes, **kwargs) -> None:
        """
        发送音频输出

        Args:
            audio_data: TTS 生成的音频数据
            **kwargs: 额外参数（format, sample_rate 等）
        """
        pass

    @abstractmethod
    async def send_control(self, signal: str, **kwargs) -> None:
        """
        发送控制信号

        Args:
            signal: 控制信号类型
            **kwargs: 额外参数
        """
        pass
