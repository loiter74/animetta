"""
Handler 基类

提供统一的事件处理接口和数据提取工具方法。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple
from loguru import logger

if TYPE_CHECKING:
    from anima.core import OutputEvent, WebSocketSend


class BaseHandler(ABC):
    """
    Handler 抽象基类

    所有事件处理器都应继承此类，实现统一的：
    - 日志格式
    - 数据提取方法
    - 错误处理

    使用示例:
        class MyHandler(BaseHandler):
            async def handle(self, event: OutputEvent) -> None:
                data, metadata = self.extract_event_data(event)
                if data is None:
                    return
                # 处理数据...
    """

    def __init__(self, websocket_send: "WebSocketSend" = None):
        """
        初始化 Handler

        Args:
            websocket_send: WebSocket 发送函数
        """
        self.websocket_send = websocket_send

    @property
    def name(self) -> str:
        """Handler 名称（用于日志）"""
        return self.__class__.__name__.replace("Handler", "").lower()

    # ========================================
    # 抽象方法
    # ========================================

    @abstractmethod
    async def handle(self, event: "OutputEvent") -> None:
        """
        处理事件

        Args:
            event: 输出事件
        """
        pass

    # ========================================
    # 统一的数据提取方法
    # ========================================

    def extract_event_data(
        self,
        event: "OutputEvent",
        expect_data_type: type = None,
        expect_metadata_keys: list = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        统一提取事件数据和元数据

        Args:
            event: 输出事件
            expect_data_type: 期望的 data 类型（如 dict, str），None 表示不检查
            expect_metadata_keys: 期望的 metadata 键列表，None 表示不检查

        Returns:
            Tuple[data, metadata]: 提取的数据和元数据
                - data: 如果类型不匹配返回 None
                - metadata: 始终返回 dict（无效时返回空 dict）
        """
        # 提取并验证 data
        data = event.data
        if expect_data_type is not None and not isinstance(data, expect_data_type):
            self._log_type_error("event.data", expect_data_type.__name__, data)
            return None, {}

        # 提取并验证 metadata
        metadata = event.metadata
        if not isinstance(metadata, dict):
            if metadata is not None:
                self._log_type_warning("event.metadata", "dict", metadata)
            metadata = {}

        return data, metadata

    def extract_dict_data(
        self,
        event: "OutputEvent",
        required_keys: list = None,
        optional_keys: list = None,
    ) -> Tuple[Optional[Dict], Dict[str, Any]]:
        """
        提取事件数据（期望 data 是 dict）

        Args:
            event: 输出事件
            required_keys: 必需的键列表，缺少则返回 None
            optional_keys: 可选的键列表

        Returns:
            Tuple[data_dict, metadata]:
                - data_dict: 如果验证失败返回 None
                - metadata: 始终返回 dict
        """
        data, metadata = self.extract_event_data(event, expect_data_type=dict)
        if data is None:
            return None, {}

        # 检查必需的键
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                logger.warning(
                    f"[{self.name}] event.data 缺少必需字段: {missing}"
                )
                return None, metadata

        return data, metadata

    def extract_text_data(
        self,
        event: "OutputEvent",
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        提取事件数据（期望 data 是 string）

        Args:
            event: 输出事件

        Returns:
            Tuple[text, metadata]:
                - text: 如果验证失败返回 None
                - metadata: 始终返回 dict
        """
        return self.extract_event_data(event, expect_data_type=str)

    # ========================================
    # 日志辅助方法
    # ========================================

    def _log_type_error(self, field: str, expected: str, actual: Any) -> None:
        """记录类型错误"""
        logger.error(
            f"[{self.name}] {field} 类型错误: 期望 {expected}, "
            f"实际 {type(actual).__name__}, 值: {str(actual)[:100]}"
        )

    def _log_type_warning(self, field: str, expected: str, actual: Any) -> None:
        """记录类型警告"""
        logger.warning(
            f"[{self.name}] {field} 类型警告: 期望 {expected}, "
            f"实际 {type(actual).__name__}, 使用默认值"
        )

    # ========================================
    # 发送方法
    # ========================================

    async def send(self, message: dict) -> None:
        if self.websocket_send is None:
            logger.warning(...)
            return
        await self.websocket_send(message) 

    async def send_error(self, message: str, seq: int = 0) -> None:
        """
        发送错误消息到前端

        Args:
            message: 错误消息
            seq: 序号
        """
        await self.send({
            "type": "error",
            "message": message,
            "seq": seq,
        })


class LifecycleHandler(BaseHandler):
    """
    带生命周期的 Handler 基类

    用于需要启动/停止的 Handler（如订阅 EventBus）

    子类应该：
    - 重写 start() 和 stop() 方法来管理订阅
    - 可以选择重写 handle() 或使用单独的处理方法
    """

    def __init__(self, websocket_send: "WebSocketSend" = None):
        super().__init__(websocket_send)
        self._is_running = False

    async def start(self) -> None:
        """启动 Handler"""
        if self._is_running:
            return
        self._is_running = True
        logger.info(f"[{self.name}] Started")

    async def stop(self) -> None:
        """停止 Handler"""
        if not self._is_running:
            return
        self._is_running = False
        logger.info(f"[{self.name}] Stopped")

    async def handle(self, event: "OutputEvent") -> None:
        """
        处理事件（默认实现）

        子类可以重写此方法，或使用单独的处理方法（如 _handle_text_input）
        """
        # 默认实现：记录警告
        logger.warning(f"[{self.name}] handle() 未实现，事件被忽略: {event.type}")

    @property
    def is_running(self) -> bool:
        """Handler 是否运行中"""
        return self._is_running