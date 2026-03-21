"""
Anima Tool Use 工具集

提供 LangChain 兼容的工具定义，支持：
1. 内置工具（web_search, get_weather, read_file, get_current_time, list_directory, calculator）
2. MCP 桥接工具（从外部 MCP 服务器动态加载）

使用示例:
    from anima.tools import load_tools_from_config

    # 从配置文件加载
    config = {
        "builtin_tools": ["web_search", "get_weather"],
        "mcp_servers": [...]
    }
    tools, tools_map = load_tools_from_config(config)
"""

from .base import (
    get_builtin_tools,
    get_tools_map,
    create_tool_registry,
    load_tools_from_config,
)

from .mcp_bridge import (
    MCPServerClient,
    MCPToolManager,
    get_mcp_manager,
    load_mcp_tools,
)

# 导出内置工具（可选，方便直接导入使用）
from .base import (
    web_search,
    get_weather,
    read_file,
    get_current_time,
    list_directory,
    calculator,
)

__all__ = [
    # 基础工具函数
    "get_builtin_tools",
    "get_tools_map",
    "create_tool_registry",
    "load_tools_from_config",

    # MCP 相关
    "MCPServerClient",
    "MCPToolManager",
    "get_mcp_manager",
    "load_mcp_tools",

    # 内置工具（可选导出）
    "web_search",
    "get_weather",
    "read_file",
    "get_current_time",
    "list_directory",
    "calculator",
]
