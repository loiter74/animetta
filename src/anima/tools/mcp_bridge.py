"""
MCP Bridge - 连接 MCP 服务器，将工具转换为 LangChain Tool

支持三种传输方式:
- stdio: 本地子进程通信
- sse: Server-Sent Events (HTTP)
- streamable_http: Streamable HTTP (MCP 新标准)
"""

from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamable_http_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class MCPClient:
    """单个 MCP 服务器连接"""

    def __init__(self, name: str, transport: str, **kwargs):
        self.name = name
        self.transport = transport
        self._config = kwargs
        self._exit_stack: Optional[AsyncExitStack] = None
        self.session: Optional[ClientSession] = None

    async def connect(self) -> bool:
        """连接到 MCP 服务器"""
        if not MCP_AVAILABLE:
            logger.warning(f"[MCP:{self.name}] mcp 包未安装")
            return False

        try:
            self._exit_stack = AsyncExitStack()

            if self.transport == "stdio":
                params = StdioServerParameters(
                    command=self._config["command"],
                    args=self._config.get("args", []),
                    env=self._config.get("env"),
                )
                read, write = await self._exit_stack.enter_async_context(
                    stdio_client(params)
                )

            elif self.transport == "sse":
                read, write = await self._exit_stack.enter_async_context(
                    sse_client(
                        url=self._config["url"],
                        headers=self._config.get("headers"),
                        timeout=self._config.get("timeout", 5),
                        sse_read_timeout=self._config.get("sse_read_timeout", 300),
                    )
                )

            elif self.transport == "streamable_http":
                streams = await self._exit_stack.enter_async_context(
                    streamable_http_client(url=self._config["url"])
                )
                read, write = streams[0], streams[1]

            else:
                logger.error(f"[MCP:{self.name}] 不支持的传输方式: {self.transport}")
                return False

            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self.session.initialize()
            logger.info(f"[MCP:{self.name}] 已连接 ({self.transport})")
            return True

        except Exception as e:
            logger.error(f"[MCP:{self.name}] 连接失败: {e}")
            await self.disconnect()
            return False

    async def disconnect(self):
        """断开连接"""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self.session = None
            logger.info(f"[MCP:{self.name}] 已断开")

    async def list_tools(self) -> List[Any]:
        """获取服务器提供的工具列表"""
        if not self.session:
            return []
        try:
            response = await self.session.list_tools()
            logger.info(f"[MCP:{self.name}] 发现 {len(response.tools)} 个工具")
            return response.tools
        except Exception as e:
            logger.error(f"[MCP:{self.name}] 获取工具列表失败: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if not self.session:
            return None
        try:
            return await self.session.call_tool(name, arguments)
        except Exception as e:
            logger.error(f"[MCP:{self.name}] 调用工具 {name} 失败: {e}")
            return None


def _parse_type(type_name: str) -> type:
    """JSON Schema 类型 -> Python 类型"""
    return {
        "string": str, "integer": int, "number": float,
        "boolean": bool, "array": list, "object": dict,
    }.get(type_name, str)


def mcp_tool_to_langchain(client: MCPClient, tool_info: Any) -> Any:
    """将 MCP 工具转换为 LangChain StructuredTool"""
    from langchain_core.tools import StructuredTool
    from pydantic import create_model

    tool_name = tool_info.name
    description = tool_info.description or ""
    schema = tool_info.inputSchema or {}

    fields = {}
    for prop_name, prop_info in schema.get("properties", {}).items():
        fields[prop_name] = (_parse_type(prop_info.get("type", "string")), ...)

    InputModel = create_model(f"{tool_name}_Input", **fields)

    async def execute(**kwargs):
        result = await client.call_tool(tool_name, kwargs)
        if result and hasattr(result, "content"):
            if isinstance(result.content, list):
                return "\n".join(
                    item.text if hasattr(item, "text") else str(item)
                    for item in result.content
                )
            return str(result.content)
        return str(result) if result else "无结果"

    return StructuredTool(
        name=tool_name,
        description=description,
        func=lambda **kw: "",
        coroutine=execute,
        args_schema=InputModel,
    )


class MCPManager:
    """管理多个 MCP 服务器连接和工具"""

    def __init__(self):
        self.clients: List[MCPClient] = []
        self.tools: List[Any] = []

    async def load(self, server_configs: List[Dict[str, Any]]) -> List[Any]:
        """连接所有服务器并加载工具"""
        if not MCP_AVAILABLE:
            logger.warning("[MCP] mcp 包未安装，跳过 MCP 工具加载")
            return []

        for cfg in server_configs:
            name = cfg.get("name", "unknown")
            transport = cfg.get("transport", "stdio")

            # 提取传输层参数
            kwargs = {}
            if transport == "stdio":
                kwargs = {k: cfg[k] for k in ("command", "args", "env") if k in cfg}
            elif transport in ("sse", "streamable_http"):
                kwargs = {k: cfg[k] for k in ("url", "headers", "timeout") if k in cfg}
                if transport == "sse" and "sse_read_timeout" in cfg:
                    kwargs["sse_read_timeout"] = cfg["sse_read_timeout"]

            client = MCPClient(name=name, transport=transport, **kwargs)
            if await client.connect():
                self.clients.append(client)

                for t in await client.list_tools():
                    try:
                        self.tools.append(mcp_tool_to_langchain(client, t))
                        logger.info(f"[MCP] 加载工具: {t.name} from {name}")
                    except Exception as e:
                        logger.error(f"[MCP] 转换工具 {t.name} 失败: {e}")

        logger.info(f"[MCP] 共加载 {len(self.tools)} 个工具 ({len(self.clients)} 个服务器)")
        return self.tools

    async def close_all(self):
        """关闭所有连接"""
        for client in self.clients:
            await client.disconnect()
        self.clients.clear()
        self.tools.clear()
