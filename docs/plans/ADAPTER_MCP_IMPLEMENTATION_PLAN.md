# Adapter Layer & MCP Layer 实现计划

基于现有 EventBus 架构的扩展方案。

---

## 现有架构

```
EventBus (事件总线)
    ├── subscribe(event_type, handler)
    ├── emit(event)
    └── unsubscribe(subscription)

EventRouter (事件路由器)
    ├── register(event_type, handler, priority)
    └── setup()

ConversationOrchestrator (对话编排器)
    ├── event_bus: EventBus
    ├── event_router: EventRouter
    ├── input_pipeline: InputPipeline
    └── output_pipeline: OutputPipeline
```

---

## 设计原则

1. **复用 EventBus** - 所有组件通过 EventBus 通信
2. **扩展事件类型** - 添加新的事件类型支持多通道和工具
3. **最小改动** - 不破坏现有功能
4. **渐进式迁移** - 可以逐步替换旧代码

---

## Part 1: Adapter Layer

### 1.1 设计思路

**ChannelAdapter** 只是一个"事件发射器"，将外部输入转换为 EventBus 事件。

```
外部输入 (Socket.IO / REST / CLI / Discord)
    ↓
ChannelAdapter.receive()
    ↓
EventBus.emit(InputEvent)
    ↓
ConversationOrchestrator (监听 InputEvent)
    ↓
处理流程 (现有)
    ↓
EventBus.emit(OutputEvent)
    ↓
ChannelAdapter.send()
```

### 1.2 扩展事件类型

```python
class EventType(str, Enum):
    # 新增：输入事件类型
    INPUT_TEXT = "input_text"
    INPUT_AUDIO = "input_audio"
    INPUT_IMAGE = "input_image"

    # 新增：通道事件类型
    CHANNEL_CONNECT = "channel_connect"
    CHANNEL_DISCONNECT = "channel_disconnect"

    # 新增：MCP 工具事件类型
    TOOL_EXECUTE = "tool_execute"
    TOOL_RESULT = "tool_result"
```

### 1.3 ChannelAdapter 接口

```python
class ChannelAdapter(ABC):
    """通道适配器基类"""

    @property
    @abstractmethod
    def channel_type(self) -> str: pass

    @abstractmethod
    async def start(self) -> None: pass

    @abstractmethod
    async def stop(self) -> None: pass

    @abstractmethod
    async def send(self, event: OutputEvent) -> None: pass
```

---

## Part 2: MCP Layer

### 2.1 设计思路

MCP 工具层也通过 EventBus 通信。

```
LLM 产生 tool_call
    ↓
EventBus.emit(TOOL_EXECUTE)
    ↓
ToolManager (监听 TOOL_EXECUTE)
    ↓
执行工具 -> 产生结果
    ↓
EventBus.emit(TOOL_RESULT)
    ↓
LLM 接收 tool_result，继续对话
```

### 2.2 工具类型

```python
class ToolPermission(Enum):
    AUTO = "auto"       # 自动允许
    SESSION = "session" # 会话内允许一次
    ASK = "ask"         # 每次询问用户
    DENY = "deny"       # 拒绝

@dataclass
class ToolCallRequest:
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
```

### 2.3 BaseTool 基类

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @abstractmethod
    async def execute(self, arguments: Dict) -> Any: pass
```

---

## Part 3: 集成到 Orchestrator

```python
class ConversationOrchestrator:
    def __init__(self, ..., tool_manager: ToolManager = None):
        self.tool_manager = tool_manager
        if tool_manager:
            self.event_router.register(
                EventType.TOOL_RESULT,
                ToolResultHandler(self),
                priority=EventPriority.HIGH
            )
```

---

## 实施步骤

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

1. **复用 EventBus** - 所有组件通过 EventBus 通信
2. **扩展事件类型** - 添加 `INPUT_*` 和 `TOOL_*` 事件类型
3. **适配器模式** - ChannelAdapter 只是"事件转换器"
4. **渐进式迁移** - 可以逐步替换现有代码
