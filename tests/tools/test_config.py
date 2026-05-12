"""Tests for tool configuration loading and validation."""

import pytest
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestLoadToolsConfig:
    """load_tools_config function tests."""

    def test_load_default_config_when_file_missing(self):
        """When config file doesn't exist, should return default config."""
        from anima.tools.config import load_tools_config

        config = load_tools_config("/tmp/nonexistent_tools.yaml")
        assert "builtin_tools" in config
        assert len(config["builtin_tools"]) == 4
        assert "calculator" in config["builtin_tools"]
        assert "mcp_servers" in config
        assert "tool_settings" in config

    def test_load_valid_yaml_config(self):
        """Loading a valid YAML config file should parse correctly."""
        from anima.tools.config import load_tools_config

        sample = {
            "builtin_tools": ["calculator", "web_search"],
            "mcp_servers": [
                {
                    "name": "filesystem",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"],
                }
            ],
            "tool_settings": {
                "max_tool_calls_per_turn": 10,
                "tool_execution_timeout": 60,
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", encoding="utf-8", delete=False
        ) as f:
            yaml.dump(sample, f)
            path = f.name

        try:
            config = load_tools_config(path)
            assert config["builtin_tools"] == ["calculator", "web_search"]
            assert len(config["mcp_servers"]) == 1
            assert config["mcp_servers"][0]["name"] == "filesystem"
            assert config["tool_settings"]["max_tool_calls_per_turn"] == 10
        finally:
            os.unlink(path)

    def test_load_empty_yaml_returns_empty_dict(self):
        """Empty YAML file should return an empty dict (falls to {}) which then
        load_tools_from_config will handle with defaults."""
        from anima.tools.config import load_tools_config

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", encoding="utf-8", delete=False
        ) as f:
            f.write("")
            path = f.name

        try:
            config = load_tools_config(path)
            assert config == {}
        finally:
            os.unlink(path)

    def test_load_invalid_yaml_returns_default(self):
        """Invalid YAML content should trigger graceful fallback to defaults."""
        from anima.tools.config import load_tools_config

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", encoding="utf-8", delete=False
        ) as f:
            f.write(":: invalid yaml :: [}")
            path = f.name

        try:
            config = load_tools_config(path)
            assert "builtin_tools" in config
        finally:
            os.unlink(path)

    def test_default_config_structure(self):
        """Default config must contain all expected keys."""
        from anima.tools.config import _get_default_config

        config = _get_default_config()
        assert "builtin_tools" in config
        assert "mcp_servers" in config
        assert "tool_settings" in config
        assert config["tool_settings"]["max_tool_calls_per_turn"] == 5
        assert config["tool_settings"]["retry_on_failure"] is True
        assert config["tool_settings"]["max_retries"] == 2


class TestValidateToolsConfig:
    """validate_tools_config function tests."""

    def test_valid_builtin_tools_only(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": ["calculator", "web_search", "get_current_time", "get_weather"],
            "mcp_servers": [],
        }
        assert validate_tools_config(config) is True

    def test_valid_mcp_stdio_server(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": [],
            "mcp_servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "test-server"],
                }
            ],
        }
        assert validate_tools_config(config) is True

    def test_valid_mcp_sse_server(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": [],
            "mcp_servers": [
                {
                    "name": "sse-server",
                    "transport": "sse",
                    "url": "http://localhost:8080/sse",
                }
            ],
        }
        assert validate_tools_config(config) is True

    def test_valid_mcp_streamable_http_server(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": [],
            "mcp_servers": [
                {
                    "name": "http-server",
                    "transport": "streamable_http",
                    "url": "http://localhost:8080/mcp",
                }
            ],
        }
        assert validate_tools_config(config) is True

    def test_mcp_server_missing_name(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": [],
            "mcp_servers": [
                {"transport": "stdio", "command": "npx"}
            ],
        }
        assert validate_tools_config(config) is False

    def test_mcp_stdio_missing_command(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": [],
            "mcp_servers": [
                {"name": "bad-server", "transport": "stdio"}
            ],
        }
        assert validate_tools_config(config) is False

    def test_mcp_sse_missing_url(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": [],
            "mcp_servers": [
                {"name": "bad-sse", "transport": "sse"}
            ],
        }
        assert validate_tools_config(config) is False

    def test_unsupported_transport(self):
        from anima.tools.config import validate_tools_config

        config = {
            "builtin_tools": [],
            "mcp_servers": [
                {"name": "bad-transport", "transport": "websocket", "url": "ws://localhost"}
            ],
        }
        assert validate_tools_config(config) is False
