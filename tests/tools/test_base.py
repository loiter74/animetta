"""Tests for built-in tools (calculator, get_current_time, load_tools_from_config)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestCalculator:
    """Calculator tool tests."""

    @pytest.mark.asyncio
    async def test_calculator_addition(self):
        from anima.tools.base import calculator
        result = await calculator.coroutine("1 + 2")
        assert "Result: 1 + 2 = 3" in result

    @pytest.mark.asyncio
    async def test_calculator_subtraction(self):
        from anima.tools.base import calculator
        result = await calculator.coroutine("10 - 4")
        assert "Result: 10 - 4 = 6" in result

    @pytest.mark.asyncio
    async def test_calculator_multiplication(self):
        from anima.tools.base import calculator
        result = await calculator.coroutine("3 * 5")
        assert "Result: 3 * 5 = 15" in result

    @pytest.mark.asyncio
    async def test_calculator_division(self):
        from anima.tools.base import calculator
        result = await calculator.coroutine("20 / 4")
        assert "Result: 20 / 4 = 5.0" in result

    @pytest.mark.asyncio
    async def test_calculator_power(self):
        from anima.tools.base import calculator
        result = await calculator.coroutine("2 ** 10")
        assert "Result: 2 ** 10 = 1024" in result

    @pytest.mark.asyncio
    async def test_calculator_invalid_expression(self):
        from anima.tools.base import calculator
        result = await calculator.coroutine("not a math expr")
        assert "Calculation failed" in result

    @pytest.mark.asyncio
    async def test_calculator_negative(self):
        from anima.tools.base import calculator
        result = await calculator.coroutine("-5 + 3")
        assert "Result: -5 + 3 = -2" in result


class TestGetCurrentTime:
    """get_current_time tool tests."""

    @pytest.mark.asyncio
    async def test_get_current_time_default(self):
        from anima.tools.base import get_current_time
        result = await get_current_time.coroutine()
        assert "Current time" in result
        assert "Asia/Shanghai" in result or "local time" in result

    @pytest.mark.asyncio
    async def test_get_current_time_utc(self):
        from anima.tools.base import get_current_time
        result = await get_current_time.coroutine(timezone="UTC")
        assert "Current time" in result
        assert "UTC" in result

    @pytest.mark.asyncio
    async def test_get_current_time_invalid_timezone(self):
        from anima.tools.base import get_current_time
        result = await get_current_time.coroutine(timezone="Invalid/Zone")
        # Should fall back to local time on error
        assert "Current local time" in result or "Current time" in result

    @pytest.mark.asyncio
    async def test_get_current_time_tokyo(self):
        from anima.tools.base import get_current_time
        result = await get_current_time.coroutine(timezone="Asia/Tokyo")
        assert "Current time" in result
        assert "Asia/Tokyo" in result


class TestLoadToolsFromConfig:
    """load_tools_from_config tests."""

    @pytest.mark.asyncio
    async def test_load_all_builtin_tools(self):
        """Loading without filter should return all 4 built-in tools."""
        from anima.tools.base import load_tools_from_config
        tools, tools_map = load_tools_from_config({"builtin_tools": None})
        assert len(tools) >= 4
        assert "web_search" in tools_map
        assert "get_weather" in tools_map
        assert "get_current_time" in tools_map
        assert "calculator" in tools_map

    @pytest.mark.asyncio
    async def test_load_filtered_builtin_tools(self):
        """Loading with a filter list should only return matching tools."""
        from anima.tools.base import load_tools_from_config
        tools, tools_map = load_tools_from_config(
            {"builtin_tools": ["calculator", "get_current_time"]}
        )
        assert len(tools) == 2
        assert "calculator" in tools_map
        assert "get_current_time" in tools_map
        assert "web_search" not in tools_map

    @pytest.mark.asyncio
    async def test_load_with_empty_builtin_filter(self):
        """Empty filter list should return no built-in tools."""
        from anima.tools.base import load_tools_from_config
        tools, tools_map = load_tools_from_config({"builtin_tools": []})
        assert len(tools) == 0
        assert tools_map == {}

    @patch("anima.tools.base.load_tools_from_config")
    def test_get_builtin_tools(self, mock_load):
        from anima.tools.base import get_builtin_tools
        tools = get_builtin_tools()
        assert len(tools) == 4
        names = [t.name for t in tools]
        assert "calculator" in names

    def test_get_tools_map(self):
        from anima.tools.base import get_builtin_tools, get_tools_map
        tools = get_builtin_tools()
        tools_map = get_tools_map(tools)
        assert "calculator" in tools_map
        assert "web_search" in tools_map

    def test_create_tool_registry_filter(self):
        from anima.tools.base import create_tool_registry
        tools, tools_map = create_tool_registry(builtin_enabled=["calculator"])
        assert len(tools) == 1
        assert tools[0].name == "calculator"

    def test_create_tool_registry_with_extra(self):
        from anima.tools.base import create_tool_registry
        from langchain_core.tools import tool

        @tool
        async def dummy_tool(param: str) -> str:
            """A dummy extra tool."""
            return f"dummy: {param}"

        tools, tools_map = create_tool_registry(
            builtin_enabled=["calculator"],
            extra_tools=[dummy_tool],
        )
        assert len(tools) == 2
        assert "calculator" in tools_map
        assert "dummy_tool" in tools_map
