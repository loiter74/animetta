"""Tests for Minecraft Tools (standalone, no full anima import)"""

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

# Import tools
import importlib.util as iu
spec = iu.spec_from_file_location(
    'anima.tools.minecraft.tools',
    'src/anima/tools/minecraft/tools.py',
)
tools_mod = iu.module_from_spec(spec)
sys.modules['anima.tools.minecraft.tools'] = tools_mod
spec.loader.exec_module(tools_mod)

get_minecraft_tools = tools_mod.get_minecraft_tools


class TestTools:
    def test_get_tools_returns_list(self):
        """get_minecraft_tools should return a non-empty list"""
        tools = get_minecraft_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        print("PASS: get_tools returns list")

    def test_tool_names(self):
        """All expected tool names should be present"""
        tools = get_minecraft_tools()
        names = [t.name for t in tools]
        expected = [
            "mc_goto", "mc_mine", "mc_build", "mc_attack",
            "mc_chat", "mc_status", "mc_goal", "mc_stop", "mc_collect",
        ]
        for name in expected:
            assert name in names, f"Missing: {name}"
        print("PASS: all 9 tool names present")

    def test_tool_count(self):
        """Should have exactly 9 tools"""
        assert len(get_minecraft_tools()) == 9
        print("PASS: exactly 9 tools")

    def test_all_tools_have_descriptions(self):
        """Every tool should have a non-empty meaningful description"""
        for t in get_minecraft_tools():
            assert t.description, f"{t.name} has no description"
            assert len(t.description) > 20, f"{t.name} description too short"
        print("PASS: all tools have meaningful descriptions")

    def test_tool_has_function_reference(self):
        """Each tool should have a .func reference"""
        for t in get_minecraft_tools():
            assert hasattr(t, "func"), f"{t.name} missing .func"
        print("PASS: all tools have .func reference")

    def test_no_duplicate_names(self):
        """Tool names should be unique"""
        tools = get_minecraft_tools()
        names = [t.name for t in tools]
        assert len(names) == len(set(names)), "Duplicate tool names!"
        print("PASS: no duplicate tool names")


if __name__ == "__main__":
    t = TestTools()
    t.test_get_tools_returns_list()
    t.test_tool_names()
    t.test_tool_count()
    t.test_all_tools_have_descriptions()
    t.test_tool_has_function_reference()
    t.test_no_duplicate_names()
    print("\n*** All tools tests PASSED! ***")
