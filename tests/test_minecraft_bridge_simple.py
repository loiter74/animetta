"""Tests for Minecraft Bridge config (standalone, no full anima import)"""

import sys
import types

# Create minimal mock packages to avoid full anima import chain
anima_pkg = types.ModuleType('anima')
anima_tools = types.ModuleType('anima.tools')
anima_minecraft = types.ModuleType('anima.tools.minecraft')

anima_pkg.__path__ = []
anima_tools.__path__ = []
anima_minecraft.__path__ = []

anima_pkg.tools = anima_tools
anima_tools.minecraft = anima_minecraft

sys.modules['anima'] = anima_pkg
sys.modules['anima.tools'] = anima_tools
sys.modules['anima.tools.minecraft'] = anima_minecraft

# Now import the config directly
import importlib.util as iu
spec = iu.spec_from_file_location(
    'anima.tools.minecraft.config',
    'src/anima/tools/minecraft/config.py',
)
config_mod = iu.module_from_spec(spec)
sys.modules['anima.tools.minecraft.config'] = config_mod
spec.loader.exec_module(config_mod)

MinecraftConfig = config_mod.MinecraftConfig
MinecraftBotConfig = config_mod.MinecraftBotConfig
MinecraftSafetyConfig = config_mod.MinecraftSafetyConfig


class TestConfig:
    def test_defaults(self):
        c = MinecraftConfig()
        assert c.enabled is False
        assert c.bot.host == "localhost"
        assert c.bot.port == 25565
        assert c.bot.username == "AnimaBot"
        assert c.safety.no_griefing is True
        assert c.safety.max_distance == 500
        print("PASS: default config")

    def test_custom(self):
        c = MinecraftConfig(
            enabled=True,
            bot=MinecraftBotConfig(host="play.example.com", port=25566, username="StreamBot"),
            safety=MinecraftSafetyConfig(max_distance=1000),
        )
        assert c.enabled is True
        assert c.bot.host == "play.example.com"
        assert c.safety.max_distance == 1000
        print("PASS: custom config")

    def test_from_dict(self):
        c = MinecraftConfig(**{"enabled": True, "bot": {"username": "MyBot"}})
        assert c.enabled is True
        assert c.bot.username == "MyBot"
        print("PASS: from dict")

    def test_model_dump_roundtrip(self):
        c = MinecraftConfig(enabled=True, bot=MinecraftBotConfig(host="localhost", port=25565, username="TestBot"))
        d = c.model_dump()
        assert d["enabled"] is True
        assert d["bot"]["username"] == "TestBot"
        c2 = MinecraftConfig(**d)
        assert c2.bot.username == "TestBot"
        print("PASS: model_dump roundtrip")


if __name__ == "__main__":
    t = TestConfig()
    t.test_defaults()
    t.test_custom()
    t.test_from_dict()
    t.test_model_dump_roundtrip()
    print("\n*** All tests PASSED! ***")
