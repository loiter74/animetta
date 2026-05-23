"""
Short-term memory storage

In-memory FIFO queue implementation for storing recent N turns of the current session.
"""

from typing import Dict, List
from collections import deque
from loguru import logger

from ..models.turns import MemoryTurn


class ShortTermMemory:
    """
    Short-term memory storage

    Features:
    - Pure in-memory operation, very fast
    - FIFO eviction policy
    - Isolated by session
    """

    def __init__(self, max_turns: int = 20):
        """
        Initialize

        Args:
            max_turns: Maximum turns per session
        """
        self._max_turns = max_turns
        self._cache: Dict[str, deque] = {}
        logger.info(f"[ShortTermMemory] Initialized, max_turns={max_turns}")

    def append(self, session_id: str, turn: MemoryTurn) -> None:
        """
        Append conversation turn to short-term memory

        Args:
            session_id: Session ID
            turn: Conversation turn
        """
        if session_id not in self._cache:
            self._cache[session_id] = deque(maxlen=self._max_turns)

        self._cache[session_id].append(turn)
        logger.debug(f"[ShortTermMemory] Appended turn: session={session_id}, turns={len(self._cache[session_id])}")

    def get_recent(self, session_id: str, max_turns: int) -> List[MemoryTurn]:
        """
        Get recent N conversation turns

        Args:
            session_id: Session ID
            max_turns: Maximum number of turns

        Returns:
            List of turns (in chronological order)
        """
        cache = self._cache.get(session_id)
        if not cache:
            return []

        # Get recent N turns
        recent = list(cache)[-max_turns:] if max_turns > 0 else list(cache)
        logger.debug(f"[ShortTermMemory] Retrieved recent turns: session={session_id}, count={len(recent)}")
        return recent

    def clear(self, session_id: str) -> None:
        """
        Clear short-term memory for a specific session

        Args:
            session_id: Session ID
        """
        if session_id in self._cache:
            del self._cache[session_id]
            logger.debug(f"[ShortTermMemory] Cleared session memory: session={session_id}")

    def clear_all(self) -> None:
        """Clear all short-term memory"""
        self._cache.clear()
        logger.info("[ShortTermMemory] Cleared all short-term memory")

    def get_session_ids(self) -> List[str]:
        """Get all session IDs"""
        return list(self._cache.keys())

    def get_turn_count(self, session_id: str) -> int:
        """Get conversation turn count for a session"""
        cache = self._cache.get(session_id)
        return len(cache) if cache else 0
