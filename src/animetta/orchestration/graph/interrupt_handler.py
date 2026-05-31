"""
Interrupt signal handler

Manages interrupt signals for each session, used to interrupt ongoing LLM generation.
"""

import asyncio

from loguru import logger


class InterruptHandler:
    """
    Interrupt signal handler

    Uses asyncio.Event as the stop signal for each session.
    """

    def __init__(self):
        # session_id -> asyncio.Event
        self._signals: dict[str, asyncio.Event] = {}

    def get_signal(self, session_id: str) -> asyncio.Event:
        """
        Get the stop signal for a session (creates if it does not exist)

        Args:
            session_id: Session ID

        Returns:
            asyncio.Event: Stop signal event
        """
        if session_id not in self._signals:
            self._signals[session_id] = asyncio.Event()
            logger.debug(f"[InterruptHandler] Created stop signal: {session_id}")
        return self._signals[session_id]

    def set_interrupt(self, session_id: str) -> None:
        """
        Set interrupt signal

        Args:
            session_id: Session ID
        """
        if session_id in self._signals:
            self._signals[session_id].set()
            logger.info(f"[InterruptHandler] Set interrupt signal: {session_id}")

    def clear_interrupt(self, session_id: str) -> None:
        """
        Clear interrupt signal (prepare for new conversation)

        Args:
            session_id: Session ID
        """
        if session_id in self._signals:
            # If already set, clear it first
            if self._signals[session_id].is_set():
                self._signals[session_id].clear()
            logger.debug(f"[InterruptHandler] Cleared interrupt signal: {session_id}")

    def is_interrupted(self, session_id: str) -> bool:
        """
        Check if interrupted

        Args:
            session_id: Session ID

        Returns:
            bool: Whether interrupt signal is set
        """
        signal = self._signals.get(session_id)
        return signal.is_set() if signal else False

    def remove_session(self, session_id: str) -> None:
        """
        Remove session (cleanup on disconnect)

        Args:
            session_id: Session ID
        """
        if session_id in self._signals:
            del self._signals[session_id]
            logger.debug(f"[InterruptHandler] Removed session: {session_id}")


# Global singleton
_global_handler: InterruptHandler = None


def get_interrupt_handler() -> InterruptHandler:
    """Get the global interrupt handler instance"""
    global _global_handler
    if _global_handler is None:
        _global_handler = InterruptHandler()
    return _global_handler
