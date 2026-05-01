"""Tests for MCP bridge graceful degradation when Docker is unavailable."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestMCPClient:
    """MCPClient handles connection failures gracefully."""

    @pytest.mark.asyncio
    async def test_connect_with_bogus_command_returns_false(self):
        """Connecting with a non-existent command should return False, not crash."""
        from anima.tools.mcp_bridge import MCPClient

        client = MCPClient(
            name="test-server",
            transport="stdio",
            command="nonexistent-command-that-will-fail",
            args=["--help"],
        )
        result = await client.connect()
        assert result is False  # Graceful degradation

    @pytest.mark.asyncio
    async def test_disconnect_without_connect(self):
        """Calling disconnect without prior connect should not raise."""
        from anima.tools.mcp_bridge import MCPClient

        client = MCPClient(name="test", transport="stdio", command="echo")
        # No connect() called
        await client.disconnect()  # Should not raise

    @pytest.mark.asyncio
    async def test_list_tools_without_session(self):
        """list_tools returns empty list when not connected."""
        from anima.tools.mcp_bridge import MCPClient

        client = MCPClient(name="test", transport="stdio", command="echo")
        tools = await client.list_tools()
        assert tools == []

    @pytest.mark.asyncio
    async def test_call_tool_without_session(self):
        """call_tool returns None when not connected."""
        from anima.tools.mcp_bridge import MCPClient

        client = MCPClient(name="test", transport="stdio", command="echo")
        result = await client.call_tool("test_tool", {"arg": "val"})
        assert result is None


class TestMCPManager:
    """MCPManager handles unavailable Docker gracefully."""

    def test_build_docker_command(self):
        """_build_docker_command constructs a valid docker run command."""
        from anima.tools.mcp_bridge import MCPManager

        mgr = MCPManager()
        command, args = mgr._build_docker_command(
            sandbox={
                "image": "anima-mcp-test",
                "mounts": ["./data:/data:rw"],
                "memory": "128m",
                "cpus": "0.5",
            },
            args=["/some/path"],
        )

        assert command == "docker"
        assert "run" in args
        assert "--rm" in args
        assert "--network" in args
        assert "none" in args
        assert "anima-mcp-test" in args
        assert "/some/path" in args

    @pytest.mark.asyncio
    async def test_load_handles_docker_unavailable(self):
        """load() should not crash when Docker is unavailable."""
        from anima.tools.mcp_bridge import MCPManager

        mgr = MCPManager()
        # Simulate a Docker-based MCP server config — Docker isn't running,
        # so this should degrade gracefully
        configs = [{
            "name": "filesystem",
            "transport": "stdio",
            "sandbox": {
                "type": "docker",
                "image": "anima-mcp-filesystem",
                "mounts": ["./data:/data:rw"],
            },
            "args": ["/data"],
        }]
        # Should not raise
        tools = await mgr.load(configs)
        assert isinstance(tools, list)
