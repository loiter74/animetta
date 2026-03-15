"""
短期记忆存储

基于内存的 FIFO 队列实现, 用于存储当前会话的最近 N 轮对话。
"""

from typing import Dict, List
from collections import deque
from loguru import logger

from ..memory_turn import MemoryTurn


class ShortTermMemory:
    """
    短期记忆存储

    特点:
    - 纯内存操作, 极快
    - FIFO 淘汰策略
    - 按会话隔离
    """

    def __init__(self, max_turns: int = 20):
        """
        初始化

        Args:
            max_turns: 每个会话的最大轮次
        """
        self._max_turns = max_turns
        self._cache: Dict[str, deque] = {}
        logger.info(f"[ShortTermMemory] 初始化完成, max_turns={max_turns}")

    def append(self, session_id: str, turn: MemoryTurn) -> None:
        """
        追加对话到短期记忆

        Args:
            session_id: 会话 ID
            turn: 对话轮次
        """
        if session_id not in self._cache:
            self._cache[session_id] = deque(maxlen=self._max_turns)

        self._cache[session_id].append(turn)
        logger.debug(f"[ShortTermMemory] 追加对话: session={session_id}, turns={len(self._cache[session_id])}")

    def get_recent(self, session_id: str, max_turns: int) -> List[MemoryTurn]:
        """
        获取最近 N 轮对话

        Args:
            session_id: 会话 ID
            max_turns: 最大轮次

        Returns:
            对话列表 (按时间正序)
        """
        cache = self._cache.get(session_id)
        if not cache:
            return []

        # 获取最近 N 轮
        recent = list(cache)[-max_turns:] if max_turns > 0 else list(cache)
        logger.debug(f"[ShortTermMemory] 获取最近对话: session={session_id}, count={len(recent)}")
        return recent

    def clear(self, session_id: str) -> None:
        """
        清除指定会话的短期记忆

        Args:
            session_id: 会话 ID
        """
        if session_id in self._cache:
            del self._cache[session_id]
            logger.debug(f"[ShortTermMemory] 清除会话记忆: session={session_id}")

    def clear_all(self) -> None:
        """清除所有短期记忆"""
        self._cache.clear()
        logger.info("[ShortTermMemory] 清除所有短期记忆")

    def get_session_ids(self) -> List[str]:
        """获取所有会话 ID"""
        return list(self._cache.keys())

    def get_turn_count(self, session_id: str) -> int:
        """获取指定会话的对话轮数"""
        cache = self._cache.get(session_id)
        return len(cache) if cache else 0
