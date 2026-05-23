"""Tests for LoggerManager configuration and singleton behavior."""

import pytest
import sys
from unittest.mock import patch, MagicMock


class TestLoggerManagerBasic:
    """LoggerManager basic operations."""

    def test_singleton_behavior(self):
        from animetta import $$$
        instance1 = LoggerManager.get_instance()
        instance2 = LoggerManager.get_instance()
        assert instance1 is instance2

    def test_initial_level_is_info(self):
        from animetta import $$$
        mgr = LoggerManager.get_instance()
        assert mgr.get_level() is not None

    def test_set_level_valid(self):
        from animetta import $$$
        mgr = LoggerManager.get_instance()
        # Save current level and restore
        original_level = mgr.get_level()
        result = mgr.set_level("DEBUG")
        assert result is True
        assert mgr.get_level() == "DEBUG"
        # Restore
        mgr.set_level(original_level)

    def test_set_level_invalid(self):
        from animetta import $$$
        mgr = LoggerManager.get_instance()
        original_level = mgr.get_level()
        result = mgr.set_level("INVALID")
        assert result is False
        # Level should remain unchanged
        mgr.set_level(original_level)

    def test_set_level_case_insensitive(self):
        from animetta import $$$
        mgr = LoggerManager.get_instance()
        original_level = mgr.get_level()
        result = mgr.set_level("debug")
        assert result is True
        assert mgr.get_level() == "DEBUG"
        mgr.set_level(original_level)

    def test_set_level_all_valid_values(self):
        from animetta import $$$
        mgr = LoggerManager.get_instance()
        original_level = mgr.get_level()
        for level in ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            result = mgr.set_level(level)
            assert result is True
            assert mgr.get_level() == level
        mgr.set_level(original_level)


class TestLoggerManagerSingleton:
    """Global logger_manager singleton."""

    def test_global_singleton_exists(self):
        from animetta import $$$
        assert logger_manager is not None
        assert hasattr(logger_manager, "set_level")
        assert hasattr(logger_manager, "get_level")

    def test_global_is_same_instance(self):
        from animetta import $$$
        assert logger_manager is LoggerManager.get_instance()

    def test_set_level_on_global(self):
        from animetta import $$$
        original = logger_manager.get_level()
        logger_manager.set_level("WARNING")
        assert logger_manager.get_level() == "WARNING"
        logger_manager.set_level(original)


class TestLoggerManagerInstantiation:
    """LoggerManager __init__ behavior."""

    def test_init_sets_up_handler(self):
        from animetta import $$$
        with patch("anima.utils.logger_manager.logger.remove") as mock_remove:
            with patch("anima.utils.logger_manager.logger.add") as mock_add:
                mock_add.return_value = 123
                mgr = LoggerManager()
                mock_remove.assert_called_once()
                mock_add.assert_called_once()
                assert mgr._handler_id == 123
                assert mgr._current_level == "INFO"
