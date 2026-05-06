"""
Anima Tools

Provides:
1. Built-in tools (web_search, get_weather, read_file, ...)
2. MCP bridge tools (loaded from external servers via MCPManager)
"""

from .base import (
    get_builtin_tools,
    get_tools_map,
    create_tool_registry,
    load_tools_from_config,
)

from .mcp_bridge import MCPManager

__all__ = [
    "get_builtin_tools",
    "get_tools_map",
    "create_tool_registry",
    "load_tools_from_config",
    "MCPManager",
]
