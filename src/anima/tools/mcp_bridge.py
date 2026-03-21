"""
MCP (Model Context Protocol) 桥接模块

职责:
1. 连接 MCP 服务器（通过 stdio 或 SSE）
2. 发现服务器提供的工具列表
3. 将每个 MCP 工具转换为 LangChain Tool 对象
4. 注入到 LangGraph 的工具列表中

依赖: mcp (pip install mcp)

配置示例 (config/tools.yaml):
  mcp_servers:
    - name: "filesystem"
      transport: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]

    - name: "web-search"
      transport: "sse"
      url: "http://localhost:8080/mcp"
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from loguru import logger
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("[MCP] mcp 包未安装，MCP 功能将不可用")


class MCPServerClient:
    """
    MCP 服务器客户端

    负责连接到 MCP 服务器并获取其提供的工具列表。
    """

    def __init__(
        self,
        name: str,
        transport: str = "stdio",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        """
        初始化 MCP 服务器客户端

        Args:
            name: 服务器名称
            transport: 传输方式 ("stdio" 或 "sse")
            command: 启动命令（stdio 模式）
            args: 命令参数（stdio 模式）
            url: 服务器 URL（sse 模式）
            env: 环境变量
        """
        self.name = name
        self.transport = transport
        self.command = command
        self.args = args or []
        self.url = url
        self.env = env or {}

        self.session: Optional[ClientSession] = None
        self._is_connected = False

    async def connect(self) -> bool:
        """
        连接到 MCP 服务器

        Returns:
            bool: 连接是否成功
        """
        if not MCP_AVAILABLE:
            logger.warning(f"[{self.name}] MCP 包未安装，跳过连接")
            return False

        try:
            if self.transport == "stdio":
                return await self._connect_stdio()
            elif self.transport == "sse":
                return await self._connect_sse()
            else:
                logger.error(f"[{self.name}] 不支持的传输方式: {self.transport}")
                return False

        except Exception as e:
            logger.error(f"[{self.name}] 连接失败: {e}")
            return False

    async def _connect_stdio(self) -> bool:
        """通过 stdio 连接 MCP 服务器"""
        try:
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env,
            )

            stdio_transport = stdio_client(server_params)

            # 创建读写流
            read, write = await stdio_transport.__aenter__()

            # 创建会话
            self.session = ClientSession(read, write)
            await self.session.__aenter__()

            # 初始化
            await self.session.initialize()

            self._is_connected = True
            logger.info(f"[{self.name}] stdio 连接成功")
            return True

        except Exception as e:
            logger.error(f"[{self.name}] stdio 连接失败: {e}")
            return False

    async def _connect_sse(self) -> bool:
        """通过 SSE 连接 MCP 服务器"""
        # SSE 连接需要额外依赖
        logger.warning(f"[{self.name}] SSE 传输暂未实现")
        return False

    async def disconnect(self) -> None:
        """断开连接"""
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"[{self.name}] 断开连接时出错: {e}")

        self._is_connected = False
        logger.info(f"[{self.name}] 已断开连接")

    async def get_tools(self) -> List[Dict[str, Any]]:
        """
        获取服务器提供的工具列表

        Returns:
            List[Dict]: 工具列表
        """
        if not self._is_connected:
            logger.warning(f"[{self.name}] 未连接，无法获取工具")
            return []

        try:
            response = await self.session.list_tools()
            tools = response.tools

            logger.info(f"[{self.name}] 发现 {len(tools)} 个工具")
            return tools

        except Exception as e:
            logger.error(f"[{self.name}] 获取工具列表失败: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self._is_connected:
            logger.error(f"[{self.name}] 未连接，无法调用工具")
            return None

        try:
            result = await self.session.call_tool(tool_name, arguments)
            return result

        except Exception as e:
            logger.error(f"[{self.name}] 调用工具 {tool_name} 失败: {e}")
            return None


def mcp_tool_to_langchain(
    mcp_client: MCPServerClient,
    tool_info: Dict[str, Any],
) -> Any:
    """
    将 MCP 工具转换为 LangChain Tool

    Args:
        mcp_client: MCP 客户端
        tool_info: MCP 工具信息

    Returns:
        LangChain Tool 对象
    """
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, create_model
    import inspect

    tool_name = tool_info.get("name", "unknown")
    tool_description = tool_info.get("description", "")
    input_schema = tool_info.get("inputSchema", {})

    # 构建参数 schema
    fields = {}
    for prop_name, prop_info in input_schema.get("properties", {}).items():
        field_type = _parse_json_schema_type(prop_info)
        fields[prop_name] = (field_type, ...)

    # 创建动态 Pydantic 模型
    InputModel = create_model(f"{tool_name}_Input", **fields)

    # 创建异步执行函数
    async def execute(**kwargs):
        result = await mcp_client.call_tool(tool_name, kwargs)
        if result and hasattr(result, "content"):
            # MCP 结果格式化
            if isinstance(result.content, list):
                return "\n".join([
                    item.get("text", str(item))
                    for item in result.content
                ])
            return str(result.content)
        return str(result) if result else "无结果"

    # 创建 LangChain 工具
    langchain_tool = StructuredTool.from_coro(
        name=tool_name,
        description=tool_description,
        func=execute,
        args_schema=InputModel,
    )

    return langchain_tool


def _parse_json_schema_type(prop_info: Dict[str, Any]) -> type:
    """
    解析 JSON Schema 类型为 Python 类型

    Args:
        prop_info: 属性信息

    Returns:
        Python 类型
    """
    type_name = prop_info.get("type", "string")

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    return type_mapping.get(type_name, str)


# ========================================
# MCP 工具加载器
# ========================================

async def load_mcp_tools(
    server_configs: List[Dict[str, Any]],
) -> List[Any]:
    """
    从多个 MCP 服务器加载工具

    Args:
        server_configs: 服务器配置列表

    Returns:
        List[Tool]: LangChain 工具列表
    """
    if not MCP_AVAILABLE:
        logger.warning("[MCP] mcp 包未安装，无法加载 MCP 工具")
        return []

    all_tools = []
    clients = []

    # 连接所有服务器
    for config in server_configs:
        client = MCPServerClient(
            name=config.get("name", "unknown"),
            transport=config.get("transport", "stdio"),
            command=config.get("command"),
            args=config.get("args"),
            url=config.get("url"),
            env=config.get("env"),
        )

        if await client.connect():
            clients.append(client)

    # 获取所有工具
    for client in clients:
        try:
            mcp_tools = await client.get_tools()

            for tool_info in mcp_tools:
                try:
                    langchain_tool = mcp_tool_to_langchain(client, tool_info)
                    all_tools.append(langchain_tool)
                    logger.info(f"[MCP] 加载工具: {tool_info.get('name')} from {client.name}")
                except Exception as e:
                    logger.error(f"[MCP] 转换工具失败: {e}")

        except Exception as e:
            logger.error(f"[{client.name}] 获取工具失败: {e}")

    # 注意: 保持客户端连接，以便后续调用工具
    # 在实际应用中，需要管理客户端的生命周期

    logger.info(f"[MCP] 共加载 {len(all_tools)} 个工具")
    return all_tools


class MCPToolManager:
    """
    MCP 工具管理器

    管理 MCP 服务器的连接和工具生命周期。
    """

    def __init__(self):
        self.clients: List[MCPServerClient] = []
        self.tools: List[Any] = []

    async def load_from_config(self, server_configs: List[Dict[str, Any]]) -> List[Any]:
        """
        从配置加载 MCP 工具

        Args:
            server_configs: 服务器配置列表

        Returns:
            List[Tool]: LangChain 工具列表
        """
        self.tools = await load_mcp_tools(server_configs)
        return self.tools

    async def close_all(self) -> None:
        """关闭所有连接"""
        for client in self.clients:
            await client.disconnect()
        self.clients.clear()
        self.tools.clear()


# 全局 MCP 工具管理器
_mcp_manager = MCPToolManager()


def get_mcp_manager() -> MCPToolManager:
    """获取全局 MCP 工具管理器"""
    return _mcp_manager
