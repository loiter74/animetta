"""
工具配置加载器

从 config/tools.yaml 加载工具配置。
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


def load_tools_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载工具配置

    Args:
        config_path: 配置文件路径（默认为 config/tools.yaml）

    Returns:
        Dict: 工具配置字典
    """
    if config_path is None:
        # 默认路径
        config_path = Path(__file__).parent.parent.parent / "config" / "tools.yaml"

    config_path = Path(config_path)

    if not config_path.exists():
        logger.warning(f"[工具配置] 配置文件不存在: {config_path}，使用默认配置")
        return _get_default_config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(f"[工具配置] 已加载配置: {config_path}")
        return config or {}

    except Exception as e:
        logger.error(f"[工具配置] 加载失败: {e}，使用默认配置")
        return _get_default_config()


def _get_default_config() -> Dict[str, Any]:
    """
    获取默认工具配置

    Returns:
        Dict: 默认配置字典
    """
    return {
        "builtin_tools": [
            "web_search",
            "get_weather",
            "read_file",
            "get_current_time",
            "list_directory",
            "calculator",
        ],
        "mcp_servers": [],
        "tool_settings": {
            "max_tool_calls_per_turn": 5,
            "tool_execution_timeout": 30,
            "retry_on_failure": True,
            "max_retries": 2,
            "log_tool_calls": True,
        },
    }


def validate_tools_config(config: Dict[str, Any]) -> bool:
    """
    验证工具配置

    Args:
        config: 工具配置字典

    Returns:
        bool: 配置是否有效
    """
    # 验证内置工具
    builtin_tools = config.get("builtin_tools", [])
    valid_builtin = {
        "web_search", "get_weather", "read_file",
        "get_current_time", "list_directory", "calculator",
    }

    for tool in builtin_tools:
        if tool not in valid_builtin:
            logger.warning(f"[工具配置] 未知的内置工具: {tool}")

    # 验证 MCP 服务器配置
    mcp_servers = config.get("mcp_servers", [])
    for server in mcp_servers:
        if "name" not in server:
            logger.error("[工具配置] MCP 服务器缺少 name 字段")
            return False

        transport = server.get("transport", "stdio")
        if transport == "stdio":
            if "command" not in server:
                logger.error(f"[工具配置] MCP 服务器 {server['name']} 缺少 command 字段")
                return False
        elif transport == "sse":
            if "url" not in server:
                logger.error(f"[工具配置] MCP 服务器 {server['name']} 缺少 url 字段")
                return False
        else:
            logger.error(f"[工具配置] 不支持的传输方式: {transport}")
            return False

    return True
