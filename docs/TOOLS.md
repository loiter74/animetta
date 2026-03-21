# Anima 工具系统使用说明

## 概述

Anima 工具系统是 Phase 3-4 的核心功能，为 AI Agent 提供工具调用能力。支持：

1. **内置工具**: 预定义的工具（web_search, get_weather, read_file 等）
2. **MCP 桥接**: 通过 MCP 协议连接外部工具服务器
3. **LangChain 集成**: 与 LangGraph 无缝集成

## 目录结构

```
src/anima/tools/
├── __init__.py          # 模块导出
├── base.py              # 内置工具定义和注册表
├── config.py            # 工具配置加载器
└── mcp_bridge.py        # MCP 协议桥接
```

## 内置工具

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| `web_search` | 互联网搜索 | `query: str`, `num_results: int = 5` |
| `get_weather` | 查询天气 | `city: str` |
| `read_file` | 读取文件 | `file_path: str`, `max_length: int = 2000` |
| `get_current_time` | 获取当前时间 | `timezone: str = "Asia/Shanghai"` |
| `list_directory` | 列出目录 | `directory: str = "."` |
| `calculator` | 数学计算 | `expression: str` |

## 配置文件

`config/tools.yaml`:

```yaml
# 启用的内置工具
builtin_tools:
  - web_search
  - get_weather
  - read_file

# MCP 服务器配置
mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]

  - name: "github"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: "your-token"

# 工具调用设置
tool_settings:
  max_tool_calls_per_turn: 5
  tool_execution_timeout: 30
  retry_on_failure: true
```

## 使用示例

### 基础使用

```python
from anima.tools import load_tools_from_config

# 加载配置
config = {
    "builtin_tools": ["web_search", "calculator"],
    "mcp_servers": []
}

tools, tools_map = load_tools_from_config(config)

# 调用工具
result = await tools_map["calculator"].ainvoke({"expression": "2 + 2"})
print(result)  # "计算结果: 2 + 2 = 4"
```

### 与 LangGraph 集成

```python
from anima.graph.orchestrator import LangGraphOrchestratorFactory

# 创建带工具的编排器
orchestrator = await LangGraphOrchestratorFactory.create(
    session_id="user-123",
    service_context=service_context,
    socketio=sio,
    enable_tools=True,
    tools_config=tools_config,
)

# 处理用户输入（自动调用工具）
result = await orchestrator.process_text("帮我搜索 Python 教程")
```

### 自定义工具

```python
from langchain_core.tools import tool

@tool
async def my_custom_tool(param: str) -> str:
    """自定义工具描述。

    Args:
        param: 参数说明
    """
    # 工具实现
    return f"结果: {param}"

# 注册工具
from anima.tools.base import create_tool_registry

tools, tools_map = create_tool_registry(
    builtin_enabled=["calculator"],
    extra_tools=[my_custom_tool],
)
```

## MCP 协议支持

### 连接 MCP 服务器

```python
from anima.tools.mcp_bridge import MCPServerClient

# 创建客户端
client = MCPServerClient(
    name="my-server",
    transport="stdio",
    command="node",
    args=["server.js"],
)

# 连接并获取工具
await client.connect()
tools_info = await client.get_tools()

# 调用工具
result = await client.call_tool("tool_name", {"arg": "value"})
```

### MCP 工具管理器

```python
from anima.tools.mcp_bridge import MCPToolManager

manager = MCPToolManager()

# 加载多个 MCP 服务器
tools = await manager.load_from_config(mcp_server_configs)

# 清理连接
await manager.close_all()
```

## 测试

运行测试：

```bash
python tests/test_tools.py
```

## 依赖

- `langchain-core >= 0.3.0`: LangChain 核心库
- `mcp >= 0.1.0`: MCP 协议支持（可选）

## 注意事项

1. **工具安全性**: 工具可以访问文件系统和网络，请谨慎配置
2. **MCP 可选**: 如果未安装 `mcp` 包，MCP 功能会被跳过
3. **错误处理**: 工具执行失败会返回错误消息，不会中断整个流程
4. **超时控制**: 建议为工具调用设置合理的超时时间

## 下一步

- 添加更多内置工具
- 完善 MCP 协议支持
- 添加工具权限管理
- 支持工具组合调用
