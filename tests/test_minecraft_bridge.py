"""Tests for Minecraft Bridge (no Node.js dependency)"""

import pytest
from anima.tools.minecraft.config import MinecraftConfig, MinecraftBotConfig, MinecraftSafetyConfig


class TestMinecraftConfig:
    def test_default_config(self):
        """Default config should have safe disabled values"""
        config = MinecraftConfig()
        assert config.enabled is False
        assert config.bot.host == "localhost"
        assert config.bot.port == 25565
        assert config.bot.username == "AnimaBot"
        assert config.bot.version is None
        assert config.safety.no_griefing is True
        assert config.safety.auto_heal is True
        assert config.safety.max_distance == 500

    def test_custom_config(self):
        """Custom config should override defaults"""
        config = MinecraftConfig(
            enabled=True,
            bot=MinecraftBotConfig(host="play.example.com", port=25566, username="StreamBot"),
            safety=MinecraftSafetyConfig(max_distance=1000),
        )
        assert config.enabled is True
        assert config.bot.host == "play.example.com"
        assert config.bot.username == "StreamBot"
        assert config.safety.max_distance == 1000

    def test_config_from_dict(self):
        """Config should be constructable from dict (for loading from YAML)"""
        config = MinecraftConfig(**{
            "enabled": True,
            "bot": {"username": "MyBot"},
        })
        assert config.enabled is True
        assert config.bot.username == "MyBot"

    def test_safety_defaults(self):
        """Safety config should be strict by default"""
        config = MinecraftSafetyConfig()
        assert config.no_griefing is True
        assert config.auto_heal is True
        assert config.max_distance == 500


class TestMinecraftBridgeModule:
    def test_get_bridge_returns_none_by_default(self):
        """get_bridge should return None before initialization"""
        from anima.tools.minecraft.bridge import get_bridge
        assert get_bridge() is None

    def test_bridge_config_roundtrip(self):
        """Config should serialize/deserialize correctly"""
        config = MinecraftConfig(
            enabled=True,
            bot=MinecraftBotConfig(host="localhost", port=25565, username="TestBot"),
        )
        d = config.model_dump()
        assert d["enabled"] is True
        assert d["bot"]["username"] == "TestBot"

        # Roundtrip
        config2 = MinecraftConfig(**d)
        assert config2.bot.username == "TestBot"
