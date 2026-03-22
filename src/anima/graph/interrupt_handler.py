"""
打断信号处理器

负责管理每个会话的打断信号，用于中断正在进行的 LLM 生成。
"""

import asyncio
from typing import Dict
from loguru import logger


class InterruptHandler:
    """
    打断信号处理器

    使用 asyncio.Event 作为每个会话的停止信号。
    """

    def __init__(self):
        # session_id -> asyncio.Event
        self._signals: Dict[str, asyncio.Event] = {}

    def get_signal(self, session_id: str) -> asyncio.Event:
        """
        获取会话的停止信号（如果不存在则创建）

        Args:
            session_id: 会话 ID

        Returns:
            asyncio.Event: 停止信号事件
        """
        if session_id not in self._signals:
            self._signals[session_id] = asyncio.Event()
            logger.debug(f"[InterruptHandler] 创建停止信号: {session_id}")
        return self._signals[session_id]

    def set_interrupt(self, session_id: str) -> None:
        """
        设置打断信号

        Args:
            session_id: 会话 ID
        """
        if session_id in self._signals:
            self._signals[session_id].set()
            logger.info(f"[InterruptHandler] 设置打断信号: {session_id}")

    def clear_interrupt(self, session_id: str) -> None:
        """
        清除打断信号（为新对话准备）

        Args:
            session_id: 会话 ID
        """
        if session_id in self._signals:
            # 如果已设置，先清除
            if self._signals[session_id].is_set():
                self._signals[session_id].clear()
            logger.debug(f"[InterruptHandler] 清除打断信号: {session_id}")

    def is_interrupted(self, session_id: str) -> bool:
        """
        检查是否被打断

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否已设置打断信号
        """
        signal = self._signals.get(session_id)
        return signal.is_set() if signal else False

    def remove_session(self, session_id: str) -> None:
        """
        移除会话（断开连接时清理）

        Args:
            session_id: 会话 ID
        """
        if session_id in self._signals:
            del self._signals[session_id]
            logger.debug(f"[InterruptHandler] 移除会话: {session_id}")


# 全局单例
_global_handler: InterruptHandler = None


def get_interrupt_handler() -> InterruptHandler:
    """获取全局打断处理器实例"""
    global _global_handler
    if _global_handler is None:
        _global_handler = InterruptHandler()
    return _global_handler
