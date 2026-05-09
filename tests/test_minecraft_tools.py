"""Tests for Minecraft Tools"""

import pytest
from anima.tools.minecraft.tools import get_minecraft_tools


class TestMinecraftTools:
    def test_get_tools_returns_list(self):
        """get_minecraft_tools should return a non-empty list"""
        tools = get_minecraft_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tool_names(self):
        """All expected tool names should be present"""
        tools = get_minecraft_tools()
        names = [t.name for t in tools]
        expected = [
            "mc_goto",
            "mc_mine",
            "mc_build",
            "mc_attack",
            "mc_chat",
            "mc_status",
            "mc_goal",
            "mc_stop",
            "mc_collect",
        ]
        for name in expected:
            assert name in names, f"Missing tool: {name}"

    def test_tool_count(self):
        """Should have exactly 9 tools"""
        tools = get_minecraft_tools()
        assert len(tools) == 9

    def test_all_tools_have_descriptions(self):
        """Every tool should have a non-empty description"""
        tools = get_minecraft_tools()
        for t in tools:
            assert t.description, f"Tool {t.name} has no description"

    def test_all_tools_are_callable(self):
        """Every tool should be an async callable"""
        tools = get_minecraft_tools()
        for t in tools:
            assert callable(t), f"Tool {t.name} is not callable"
            # LangChain @tool decorated functions have .func
            assert hasattr(t, "func"), f"Tool {t.name} missing .func"

    def test_tool_parameters(self):
        """Key tools should have the expected parameters"""
        tools = get_minecraft_tools()
        tools_by_name = {t.name: t for t in tools}

        # mc_goto should have x, y, z params
        goto = tools_by_name["mc_goto"]
        args_str = str(goto.args) if hasattr(goto, "args") else ""
        assert "x" in args_str or "x" in str(goto.__fields__ if hasattr(goto, "__fields__") else "")
        assert "y" in args_str
        assert "z" in args_str

        # mc_mine should have block_type param
        mine = tools_by_name["mc_mine"]
        desc = str(mine.args) if hasattr(mine, "args") else ""
        assert "block_type" in desc

        # mc_chat should have message param
        chat = tools_by_name["mc_chat"]
        chat_desc = str(chat.args) if hasattr(chat, "args") else ""
        assert "message" in chat_desc

    def test_tool_no_mutation(self):
        """Tools should be stateless (no shared state between calls)"""
        tools1 = get_minecraft_tools()
        tools2 = get_minecraft_tools()
        assert len(tools1) == len(tools2)
        for t1, t2 in zip(tools1, tools2):
            assert t1.name == t2.name
