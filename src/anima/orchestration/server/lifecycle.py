"""
服务器生命周期管理
优雅关闭和资源清理
"""

import signal
import sys
import asyncio
from loguru import logger
from typing import Callable, Optional


class LifecycleManager:
    """
    生命周期管理器

    负责：
    1. 信号处理器注册
    2. 优雅关闭
    3. 资源清理
    """

    def __init__(self):
        self._shutdown_event: Optional[asyncio.Event] = None
        self._cleanup_callbacks: list = []
        self._signal_handlers_set = False
        self._shutting_down = False

    def setup_signal_handlers(self, shutdown_event: asyncio.Event) -> None:
        """
        设置信号处理器

        Args:
            shutdown_event: 关闭事件
        """
        self._shutdown_event = shutdown_event

        # Windows 和 Unix 都支持的信号
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Windows 特有的信号
        if hasattr(signal, 'CTRL_BREAK_EVENT'):
            try:
                signal.signal(signal.CTRL_BREAK_EVENT, self._signal_handler)
            except (ValueError, OSError):
                pass

        if hasattr(signal, 'CTRL_C_EVENT'):
            try:
                signal.signal(signal.CTRL_C_EVENT, self._signal_handler)
            except (ValueError, OSError):
                pass

        self._signal_handlers_set = True
        logger.debug("信号处理器已设置")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        # 防止重复处理
        if self._shutting_down:
            logger.info("已在关闭中，忽略重复信号")
            return

        self._shutting_down = True
        signal_name = signal.Signals(signum).name
        logger.info(f"收到信号 {signal_name}，准备优雅关闭...")

        # 执行同步清理回调
        for callback in self._cleanup_callbacks:
            try:
                # 对于异步回调，在同步上下文中我们只能尽力而为
                if asyncio.iscoroutinefunction(callback):
                    logger.warning("异步清理回调在信号处理器中无法执行，跳过")
                else:
                    callback()
            except Exception as e:
                logger.error(f"清理回调执行失败: {e}")

        logger.info("资源清理完成，退出进程")
        sys.exit(0)

    def register_cleanup_callback(self, callback: Callable) -> None:
        """
        注册清理回调函数

        Args:
            callback: 清理函数
        """
        self._cleanup_callbacks.append(callback)

    async def cleanup_all(self) -> None:
        """执行所有清理回调"""
        logger.info("开始清理资源...")

        for callback in self._cleanup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"清理回调执行失败: {e}")

        logger.info("资源清理完成")

    @property
    def is_shutdown_requested(self) -> bool:
        """是否已请求关闭"""
        return self._shutting_down
