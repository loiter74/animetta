"""
Live2D Action Queue
管理 Live2D 模型的动作队列，参考 open-yachiyo 实现
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional, Literal, Dict, Any
from enum import Enum
from loguru import logger


class OverflowPolicy(Enum):
    """队列溢出策略"""
    DROP_OLDEST = "drop_oldest"  # 丢弃最旧的
    DROP_NEWEST = "drop_newest"  # 丢弃最新的
    REJECT = "reject"             # 拒绝新动作


class QueuePolicy(Enum):
    """动作队列策略"""
    APPEND = "append"       # 追加到队列末尾
    REPLACE = "replace"     # 清空队列并执行新动作
    INTERRUPT = "interrupt" # 立即中断当前动作并执行新动作


@dataclass
class ActionMessage:
    """动作消息"""
    action_id: str
    action: dict
    duration_sec: float = 0.5
    queue_policy: str = "append"

    def __post_init__(self):
        if isinstance(self.queue_policy, str):
            self.queue_policy = QueuePolicy(self.queue_policy)


class Live2DActionMutex:
    """
    Live2D 动作互斥锁

    确保同一时间只有一个动作在执行，
    防止动作冲突（如同时播放多个 motion）
    """

    def __init__(self, cooldown_ms: int = 250):
        self.cooldown_ms = cooldown_ms
        self._last_action_end: float = 0
        self._is_executing: bool = False
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """获取互斥锁"""
        async with self._lock:
            # 检查冷却时间
            elapsed_ms = (time.time() - self._last_action_end) * 1000
            if elapsed_ms < self.cooldown_ms:
                await asyncio.sleep((self.cooldown_ms - elapsed_ms) / 1000)

            # 检查是否正在执行
            if self._is_executing:
                return False

            self._is_executing = True
            return True

    async def release(self):
        """释放互斥锁"""
        async with self._lock:
            self._is_executing = False
            self._last_action_end = time.time()


class Live2DActionQueue:
    """
    Live2D 动作队列

    功能：
    1. 管理动作队列（FIFO）
    2. 处理队列溢出
    3. 动作互斥锁
    4. 异步执行动作
    """

    def __init__(
        self,
        max_size: int = 120,
        overflow_policy: OverflowPolicy = OverflowPolicy.DROP_OLDEST,
        mutex: Optional[Live2DActionMutex] = None
    ):
        self.max_size = max_size
        self.overflow_policy = overflow_policy
        self.queue: List[ActionMessage] = []
        self.mutex = mutex or Live2DActionMutex()

        # 执行状态
        self._is_processing = False
        self._current_action: Optional[ActionMessage] = None

        # 动作执行回调
        self._execute_callback: Optional[callable] = None

    def set_execute_callback(self, callback: callable):
        """设置动作执行回调"""
        self._execute_callback = callback

    async def enqueue(self, action: ActionMessage) -> Dict[str, Any]:
        """
        入队动作

        Args:
            action: 动作消息

        Returns:
            操作结果
        """
        # 处理队列策略
        if isinstance(action.queue_policy, str):
            action.queue_policy = QueuePolicy(action.queue_policy)

        if action.queue_policy == QueuePolicy.REPLACE:
            # 清空队列
            self.queue.clear()
            # 中断当前动作
            if self._is_processing:
                await self._interrupt_current()

        elif action.queue_policy == QueuePolicy.INTERRUPT:
            # 清空队列并中断当前动作
            self.queue.clear()
            if self._is_processing:
                await self._interrupt_current()

        # 检查队列是否已满
        if len(self.queue) >= self.max_size:
            if self.overflow_policy == OverflowPolicy.DROP_OLDEST:
                self.queue.pop(0)
                logger.debug("[ActionQueue] 队列已满，丢弃最旧动作")
            elif self.overflow_policy == OverflowPolicy.DROP_NEWEST:
                return {"ok": False, "reason": "queue_overflow"}
            elif self.overflow_policy == OverflowPolicy.REJECT:
                return {"ok": False, "reason": "queue_full"}

        # 入队
        self.queue.append(action)
        logger.debug(f"[ActionQueue] 动作入队: {action.action_id}, 队列长度: {len(self.queue)}")

        # 启动处理
        if not self._is_processing:
            self._process_task = asyncio.create_task(self._process_queue())
            # 添加错误处理
            self._process_task.add_done_callback(self._handle_task_exception)

        return {"ok": True, "queue_size": len(self.queue)}

    async def _interrupt_current(self):
        """中断当前动作"""
        if self._current_action:
            logger.info(f"[ActionQueue] 中断动作: {self._current_action.action_id}")
            # TODO: 通知客户端中断当前动作
        await self.mutex.release()
        self._is_processing = False
        self._current_action = None

    async def _process_queue(self):
        """处理队列中的动作"""
        if self._is_processing:
            return

        self._is_processing = True

        try:
            while self.queue:
                # 获取下一个动作
                action = self.queue.pop(0)
                self._current_action = action

                # 等待互斥锁
                acquired = await self.mutex.acquire()
                if not acquired:
                    logger.warning(f"[ActionQueue] 无法获取互斥锁，跳过动作: {action.action_id}")
                    continue

                try:
                    # 执行动作
                    logger.info(f"[ActionQueue] 执行动作: {action.action_id}, 类型: {action.action.get('type')}")
                    await self._execute_action(action)

                    # 等待动作完成
                    await asyncio.sleep(action.duration_sec)

                finally:
                    # 释放互斥锁
                    await self.mutex.release()

        finally:
            self._is_processing = False
            self._current_action = None

    async def _execute_action(self, action: ActionMessage):
        """执行单个动作"""
        if self._execute_callback:
            await self._execute_callback(action)
        else:
            logger.warning(f"[ActionQueue] 没有设置执行回调，动作未执行: {action.action_id}")

    def clear(self):
        """清空队列"""
        self.queue.clear()
        logger.debug("[ActionQueue] 队列已清空")

    @property
    def queue_size(self) -> int:
        """获取队列大小"""
        return len(self.queue)

    @property
    def is_processing(self) -> bool:
        """是否正在处理"""
        return self._is_processing

    @property
    def current_action(self) -> Optional[ActionMessage]:
        """获取当前执行的动作"""
        return self._current_action


# ==================== 动作工厂 ====================

class ActionFactory:
    """动作消息工厂"""

    @staticmethod
    def expression(expression_name: str, intensity: str = "medium") -> ActionMessage:
        """创建表情动作"""
        return ActionMessage(
            action_id=f"expr_{expression_name}_{intensity}_{time.time()}",
            action={
                "type": "expression",
                "name": expression_name,
                "intensity": intensity
            },
            duration_sec=0.3
        )

    @staticmethod
    def motion(group: str, index: int, expression: str = None) -> ActionMessage:
        """创建动作"""
        action_data = {
            "type": "motion",
            "group": group,
            "index": index
        }
        if expression:
            action_data["expression"] = expression

        return ActionMessage(
            action_id=f"motion_{group}_{index}_{time.time()}",
            action=action_data,
            duration_sec=1.0
        )

    @staticmethod
    def param(param_name: str, value: float) -> ActionMessage:
        """创建参数动作"""
        return ActionMessage(
            action_id=f"param_{param_name}_{value}_{time.time()}",
            action={
                "type": "param",
                "name": param_name,
                "value": value
            },
            duration_sec=0.1
        )

    @staticmethod
    def sequence(actions: List[dict], total_duration: float) -> ActionMessage:
        """创建序列动作"""
        return ActionMessage(
            action_id=f"seq_{time.time()}",
            action={
                "type": "sequence",
                "actions": actions
            },
            duration_sec=total_duration
        )
