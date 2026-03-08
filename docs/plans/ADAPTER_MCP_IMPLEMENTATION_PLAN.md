# Anima Adapter Layer & MCP Layer Implementation Plan (v2)

基于现有 EventBus 架构的扩展方案。

## 现有架构

Anima 已有的核心架构：

```
EventBus (事件总线)
    ├── subscribe(event_type, handler) -> Subscription
    ├── emit(event) -> int
    └── unsubscribe(subscription)

EventRouter (事件路由器)
    ├── register(event_type, handler, priority)
    └── setup() -> 连接到 EventBus

ConversationOrchestrator (对话编排器)
    ├── event_bus: EventBus
    ├── event_router: EventRouter
    ├── input_pipeline: InputPipeline
    └── output_pipeline: OutputPipeline

Pipeline (管线)
    ├── InputPipeline: ASRStep -> TextCleanStep -> LocalLLMStep
    └── OutputPipeline: 句子分割 -> TTS调度

事件类型 (EventType)
    ├── SENTENCE        # 文本句子
    ├── AUDIO           # 音频数据
    ├── TOOL_CALL       # 工具调用 (已有!)
    ├── CONTROL         # 控制信号
    ├── EXPRESSION      # Live2D 表情
    └── AUDIO_WITH_EXPRESSION  # 音频+表情
```

## 设计原则

1. **复用 EventBus** - 所有组件通过 EventBus 通信
2. **扩展事件类型** - 添加新的事件类型支持多通道和工具
3. **最小改动** - 不破坏现有功能
4. **渐进式迁移** - 可以逐步替换旧代码

---

## Part 1: Adapter Layer (基于 EventBus)

### 1.1 设计思路

**ChannelAdapter** 只是一个"事件发射器"，将外部输入转换为 EventBus 事件：

```
外部输入 (Socket.IO / REST / CLI / Discord)
        ↓
ChannelAdapter.receive()
        ↓
EventBus.emit(InputEvent)  # 新事件类型
        ↓
ConversationOrchestrator (监听 InputEvent)
        ↓
处理流程 (现有)
        ↓
EventBus.emit(OutputEvent)  # 现有
        ↓
ChannelAdapter.send()  # 发送给客户端
```

### 1.2 扩展事件类型

在 `events/models.py` 中添加：

```python
class EventType(str, Enum):
    # ... 现有类型 ...

    # 新增：输入事件类型
    INPUT_TEXT = "input_text"       # 文本输入
    INPUT_AUDIO = "input_audio"     # 音频输入
    INPUT_IMAGE = "input_image"     # 图片输入

    # 新增：通道事件类型
    CHANNEL_CONNECT = "channel_connect"     # 通道连接
    CHANNEL_DISCONNECT = "channel_disconnect"  # 通道断开

    # 新增：MCP 工具事件类型
    TOOL_EXECUTE = "tool_execute"       # 请求执行工具
    TOOL_RESULT = "tool_result"         # 工具执行结果
```

### 1.3 通道消息结构

```python
@dataclass
class ChannelMessage:
    """通道消息（用于输入事件）"""
    channel_id: str           # 通道实例 ID
    channel_type: str         # socketio / rest / cli / discord
    session_id: str           # 会话 ID
    content: Any              # 消息内容
    user_id: Optional[str]    # 用户 ID
    metadata: Dict[str, Any]  # 元数据
```

### 1.4 ChannelAdapter 接口

```python
# src/anima/adapters/base.py

from abc import ABC, abstractmethod
from typing import Optional
from anima.events import EventBus

class ChannelAdapter(ABC):
    """
    通道适配器基类

    职责：
    1. 接收外部输入 -> 发送 InputEvent 到 EventBus
    2. 订阅 OutputEvent -> 发送给外部客户端
    """

    def __init__(self, event_bus: EventBus, channel_id: str):
        self.event_bus = event_bus
        self.channel_id = channel_id
        self._subscription = None

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """通道类型标识"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动适配器"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止适配器"""
        pass

    @abstractmethod
    async def send(self, event: "OutputEvent") -> None:
        """发送输出事件到客户端"""
        pass

    def _subscribe_output(self) -> None:
        """订阅输出事件"""
        self._subscription = self.event_bus.subscribe_all(
            self._handle_output_event
        )

    async def _handle_output_event(self, event: "OutputEvent") -> None:
        """处理输出事件（发送给客户端）"""
        await self.send(event)

    async def _emit_input(
        self,
        content: Any,
        event_type: str = EventType.INPUT_TEXT,
        session_id: str = None,
        user_id: str = None,
        metadata: dict = None
    ) -> None:
        """发送输入事件到 EventBus"""
        from anima.events import OutputEvent

        message = ChannelMessage(
            channel_id=self.channel_id,
            channel_type=self.channel_type,
            session_id=session_id or "default",
            content=content,
            user_id=user_id,
            metadata=metadata or {}
        )

        event = OutputEvent(
            type=event_type,
            data=message,
        )

        await self.event_bus.emit(event)
```

### 1.5 文件结构

```
src/anima/adapters/
├── __init__.py
├── base.py              # ChannelAdapter 基类
├── types.py             # ChannelMessage 等类型
├── registry.py          # 适配器注册表
└── implementations/
    ├── __init__.py
    ├── socketio.py      # Socket.IO 适配器（重构现有代码）
    ├── rest.py          # REST API 适配器（可选）
    └── cli.py           # CLI 适配器（可选）
```

### 1.6 Socket.IO 适配器迁移

**现状**：`socketio_server.py` 直接处理所有事件

**目标**：将 Socket.IO 事件转换为 EventBus 事件

```python
# src/anima/adapters/implementations/socketio.py

class SocketIOAdapter(ChannelAdapter):
    """Socket.IO 适配器"""

    @property
    def channel_type(self) -> str:
        return "socketio"

    async def start(self) -> None:
        # 订阅 EventBus 输出事件
        self._subscribe_output()

    async def stop(self) -> None:
        if self._subscription:
            self.event_bus.unsubscribe(self._subscription)

    async def send(self, event: OutputEvent) -> None:
        """将 EventBus 事件发送到 Socket.IO 客户端"""
        # 转换事件格式并发送
        await self._sio.emit(event.type, event.to_dict(), to=self._sid)

    # Socket.IO 事件处理器
    async def on_text_input(self, sid: str, data: dict):
        """处理文本输入"""
        await self._emit_input(
            content=data.get("text", ""),
            event_type=EventType.INPUT_TEXT,
            session_id=sid,
            metadata=data.get("metadata", {})
        )

    async def on_audio_data(self, sid: str, data: dict):
        """处理音频输入"""
        await self._emit_input(
            content=data.get("audio", []),
            event_type=EventType.INPUT_AUDIO,
            session_id=sid,
        )
```

---

## Part 2: MCP Layer (基于 EventBus)

### 2.1 设计思路

MCP 工具层也通过 EventBus 通信：

```
LLM 产生 tool_call
        ↓
EventBus.emit(TOOL_EXECUTE)  # 请求执行工具
        ↓
ToolManager (监听 TOOL_EXECUTE)
        ↓
执行工具 -> 产生结果
        ↓
EventBus.emit(TOOL_RESULT)  # 工具结果
        ↓
LLM 接收 tool_result，继续对话
```

### 2.2 工具类型定义

```python
# src/anima/mcp/types.py

from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Awaitable, Optional, Literal
from enum import Enum


class ToolPermission(Enum):
    """工具权限"""
    AUTO = "auto"           # 自动允许
    SESSION = "session"     # 会话内允许一次
    ASK = "ask"             # 每次询问用户
    DENY = "deny"           # 拒绝


@dataclass
class ToolSchema:
    """工具 Schema (兼容 OpenAI/Anthropic)"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    required: list[str] = field(default_factory=list)


@dataclass
class ToolCallRequest:
    """工具调用请求"""
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    channel_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class ToolCallResult:
    """工具调用结果"""
    tool_call_id: str
    success: bool
    result: Any
    error: Optional[str] = None


@dataclass
class ToolDefinition:
    """工具定义"""
    schema: ToolSchema
    handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    permission: ToolPermission = ToolPermission.AUTO
    dangerous: bool = False
```

### 2.3 BaseTool 基类

```python
# src/anima/mcp/base.py

from abc import ABC, abstractmethod
from .types import ToolSchema, ToolPermission

class BaseTool(ABC):
    """工具基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    def permission(self) -> ToolPermission:
        """权限级别"""
        return ToolPermission.AUTO

    @property
    def dangerous(self) -> bool:
        """是否危险"""
        return False

    @abstractmethod
    def get_schema(self) -> ToolSchema:
        """获取 JSON Schema"""
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        pass
```

### 2.4 ToolManager

```python
# src/anima/mcp/manager.py

from anima.events import EventBus, EventType, OutputEvent
from .types import ToolDefinition, ToolCallRequest, ToolCallResult
from .registry import ToolRegistry

class ToolManager:
    """
    工具管理器

    职责：
    1. 注册工具
    2. 监听 TOOL_EXECUTE 事件
    3. 执行工具并发送 TOOL_RESULT 事件
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.registry = ToolRegistry()
        self._subscription = None

    def register_tool(self, tool: BaseTool) -> None:
        """注册工具"""
        self.registry.register(tool)

    def start(self) -> None:
        """启动工具管理器"""
        self._subscription = self.event_bus.subscribe(
            EventType.TOOL_EXECUTE,
            self._handle_tool_execute
        )

    def stop(self) -> None:
        """停止工具管理器"""
        if self._subscription:
            self.event_bus.unsubscribe(self._subscription)

    async def _handle_tool_execute(self, event: OutputEvent) -> None:
        """处理工具执行请求"""
        request: ToolCallRequest = event.data

        # 查找工具
        tool = self.registry.get(request.tool_name)
        if not tool:
            await self._emit_result(ToolCallResult(
                tool_call_id=request.tool_call_id,
                success=False,
                result=None,
                error=f"Tool not found: {request.tool_name}"
            ))
            return

        # 检查权限
        # TODO: 权限检查逻辑

        # 执行工具
        try:
            result = await tool.execute(request.arguments)
            await self._emit_result(ToolCallResult(
                tool_call_id=request.tool_call_id,
                success=True,
                result=result
            ))
        except Exception as e:
            await self._emit_result(ToolCallResult(
                tool_call_id=request.tool_call_id,
                success=False,
                result=None,
                error=str(e)
            ))

    async def _emit_result(self, result: ToolCallResult) -> None:
        """发送工具结果事件"""
        event = OutputEvent(
            type=EventType.TOOL_RESULT,
            data=result,
        )
        await self.event_bus.emit(event)

    def get_all_schemas(self) -> list[ToolSchema]:
        """获取所有工具的 Schema"""
        return [tool.get_schema() for tool in self.registry.all()]
```

### 2.5 内置工具示例

```python
# src/anima/mcp/tools/time_tool.py

from ..base import BaseTool
from ..types import ToolSchema
from datetime import datetime

class TimeTool(BaseTool):
    """获取当前时间工具"""

    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "获取当前日期和时间"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "时间格式，如 '%Y-%m-%d %H:%M:%S'",
                        "default": "%Y-%m-%d %H:%M:%S"
                    }
                }
            }
        )

    async def execute(self, arguments: dict) -> str:
        fmt = arguments.get("format", "%Y-%m-%d %H:%M:%S")
        return datetime.now().strftime(fmt)


# src/anima/mcp/tools/memory_tool.py

class MemorySearchTool(BaseTool):
    """搜索记忆工具"""

    def __init__(self, memory_system):
        self.memory_system = memory_system

    @property
    def name(self) -> str:
        return "search_memory"

    @property
    def description(self) -> str:
        return "搜索对话历史和记忆"

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        )

    async def execute(self, arguments: dict) -> list:
        query = arguments["query"]
        limit = arguments.get("limit", 5)

        results = await self.memory_system.search(query, limit=limit)
        return [r.to_dict() for r in results]
```

### 2.6 文件结构

```
src/anima/mcp/
├── __init__.py
├── types.py             # 工具类型定义
├── base.py              # BaseTool 基类
├── registry.py          # 工具注册表
├── manager.py           # ToolManager
├── permissions.py       # 权限管理（可选）
└── tools/
    ├── __init__.py
    ├── time_tool.py     # 时间工具
    ├── memory_tool.py   # 记忆搜索工具
    ├── web_search.py    # 网页搜索工具
    └── calculator.py    # 计算器工具
```

---

## Part 3: 集成到 ConversationOrchestrator

### 3.1 修改 Orchestrator

```python
# 在 ConversationOrchestrator 中添加工具支持

class ConversationOrchestrator:
    def __init__(self, ..., tool_manager: ToolManager = None):
        # ... 现有代码 ...

        # 添加工具管理器
        self.tool_manager = tool_manager
        if tool_manager:
            # 订阅工具结果事件
            self.event_router.register(
                EventType.TOOL_RESULT,
                ToolResultHandler(self),
                priority=EventPriority.HIGH
            )

    async def _process_conversation(self, ctx, text):
        # ... 现有代码 ...

        # 获取 Agent 响应流（带工具调用支持）
        agent_stream = self.agent.chat_stream(
            text,
            tools=self.tool_manager.get_all_schemas() if self.tool_manager else None
        )

        # 处理流式响应，检测工具调用
        async for chunk in agent_stream:
            if chunk.type == "tool_call":
                # 发送工具执行请求
                await self.event_bus.emit(OutputEvent(
                    type=EventType.TOOL_EXECUTE,
                    data=ToolCallRequest(
                        tool_call_id=chunk.tool_call_id,
                        tool_name=chunk.tool_name,
                        arguments=chunk.arguments,
                        session_id=self.session_id
                    )
                ))
            else:
                # 正常文本块
                await self._handle_text_chunk(chunk)
```

---

## Part 4: 实施步骤

### Phase 1: 事件类型扩展 (0.5 天)

1. 在 `events/models.py` 添加新事件类型
2. 添加 `ChannelMessage` 数据类

### Phase 2: Adapter 基础设施 (1 天)

1. 创建 `adapters/` 目录
2. 实现 `ChannelAdapter` 基类
3. 实现 `AdapterRegistry`

### Phase 3: Socket.IO 迁移 (1-2 天)

1. 实现 `SocketIOAdapter`
2. 修改 `socketio_server.py` 使用适配器
3. 测试兼容性

### Phase 4: MCP 基础设施 (1 天)

1. 创建 `mcp/` 目录
2. 实现工具类型和基类
3. 实现 `ToolManager` 和 `ToolRegistry`

### Phase 5: 内置工具 (1-2 天)

1. 实现 `TimeTool`
2. 实现 `MemorySearchTool`
3. 实现 `CalculatorTool`

### Phase 6: LLM 集成 (1 天)

1. 修改 LLM 接口支持工具调用
2. 修改 `ConversationOrchestrator` 处理工具调用

### Phase 7: 测试和文档 (1 天)

1. 单元测试
2. 集成测试
3. 更新文档

---

## Part 5: 时间线

| 阶段 | 内容 | 时间 |
|------|------|------|
| 1 | 事件类型扩展 | 0.5 天 |
| 2 | Adapter 基础设施 | 1 天 |
| 3 | Socket.IO 迁移 | 1-2 天 |
| 4 | MCP 基础设施 | 1 天 |
| 5 | 内置工具 | 1-2 天 |
| 6 | LLM 集成 | 1 天 |
| 7 | 测试和文档 | 1 天 |
| **总计** | | **7-9 天** |

---

## 总结

这个方案的核心思想是：

1. **复用 EventBus** - 所有组件通过 EventBus 通信，不引入新的通信机制
2. **扩展事件类型** - 添加 `INPUT_*` 和 `TOOL_*` 事件类型
3. **适配器模式** - ChannelAdapter 只是"事件转换器"
4. **渐进式迁移** - 可以逐步替换现有代码，不影响现有功能

这样改动最小，而且完全符合 Anima 现有的架构风格。
