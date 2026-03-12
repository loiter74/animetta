"""
Live2D 动作队列管理
管理 Live2D 动作的排队和执行
"""

from typing import Optional, Callable, Any
from loguru import logger


class Live2DManager:
    """
    Live2D 管理器

    负责：
    1. 管理 Live2D 动作队列
    2. 执行动作并广播到客户端
    """

    def __init__(self):
        self._action_queue = None
        self._execute_callback: Optional[Callable] = None

    @property
    def action_queue(self):
        """获取 Live2D 动作队列（延迟初始化）"""
        if self._action_queue is None:
            from anima.services.live2d import Live2DActionQueue
            self._action_queue = Live2DActionQueue()
            logger.info("[Live2D] 动作队列已初始化")

        return self._action_queue

    def set_execute_callback(self, callback: Callable[[Any], None]) -> None:
        """
        设置动作执行回调

        Args:
            callback: 异步回调函数，接收 ActionMessage 参数
        """
        self._execute_callback = callback

        if self._action_queue:
            self._action_queue.set_execute_callback(callback)
            logger.info("[Live2D] 动作执行回调已设置")

    async def enqueue_action(
        self,
        action_data: dict,
        action_id: str = "",
        queue_policy: str = "append",
        duration: float = 0.5
    ) -> dict:
        """
        将动作加入队列

        Args:
            action_data: 动作数据
            action_id: 动作 ID
            queue_policy: 队列策略 ("append", "replace", "immediate")
            duration: 持续时间

        Returns:
            dict: 入队结果
        """
        from anima.services.live2d import ActionMessage

        action = ActionMessage(
            action_id=action_id,
            action=action_data,
            duration_sec=duration,
            queue_policy=queue_policy
        )

        result = await self.action_queue.enqueue(action)
        logger.info(f"[Live2D] 动作已入队: {action_id}, 结果: {result}")

        return result

    def is_initialized(self) -> bool:
        """检查动作队列是否已初始化"""
        return self._action_queue is not None
