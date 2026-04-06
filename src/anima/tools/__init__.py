"""
Anima 工具集

提供:
1. 内置工具 (web_search, get_weather, read_file, ...)
2. MCP 桥接工具 (通过 MCPManager 从外部服务器加载)
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
