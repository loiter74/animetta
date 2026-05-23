"""
Loguru logger manager
Supports dynamic level switching
"""

from loguru import logger
import sys
from typing import Optional


class LoggerManager:
    """Loguru logger manager, supports dynamic level switching"""

    _instance: Optional["LoggerManager"] = None

    def __init__(self):
        self._handler_id = None
        self._current_level = "INFO"
        self._setup_handler()

    @classmethod
    def get_instance(cls) -> "LoggerManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _setup_handler(self, level: str = "INFO"):
        """Setup log handler"""
        logger.remove()
        self._handler_id = logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True,
        )
        self._current_level = level

    def set_level(self, level: str) -> bool:
        """Dynamically set log level"""
        level = level.upper()
        valid_levels = ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        if level not in valid_levels:
            logger.warning(f"Invalid log level: {level}")
            return False

        self._setup_handler(level)
        logger.info(f"Log level updated to: {level}")
        return True

    def get_level(self) -> str:
        return self._current_level


# Global singleton
logger_manager = LoggerManager.get_instance()
