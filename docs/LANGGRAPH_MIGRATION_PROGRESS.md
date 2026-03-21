# EventBus → LangGraph 架构迁移进度

## 概述

本文档记录 Anima 从自定义 EventBus 架构迁移到 LangGraph 状态图架构的进度。

## 迁移目标

1. 引入 Tool Use / Agent 能力
2. 支持 MCP 协议
3. 对齐行业主流 AI Agent 技术栈

## 当前状态：Phase 1-6 已完成 ✅

迁移已完成！Anima 现在完全使用 LangGraph 架构，所有旧代码已清理。

### Phase 0: 环境准备 ✅

- [x] 添加 LangGraph 依赖到 `requirements.txt`
  - `langgraph>=0.2.0`
  - `langchain>=0.3.0`
  - `langchain-core>=0.3.0`
  - `langchain-openai>=0.2.0`
  - `langchain-community>=0.3.0`
  - `mcp>=0.1.0` (Phase 4 新增)

### Phase 1: 定义 LangGraph 状态 ✅

#### 1.1 创建全局状态定义 ✅

**文件**: `src/anima/graph/state.py`

**内容**:
- `AgentState` TypedDict - 包含所有对话流程数据
- `create_initial_state()` - 创建初始状态
- `create_user_message()` - 创建用户消息
- `create_ai_message()` - 创建 AI 消息
- `create_system_message()` - 创建系统消息

**状态字段**:
```python
class AgentState(TypedDict):
    # 输入相关
    input_type: str                  # 'text' 或 'audio'
    raw_audio: Optional[bytes]       # 原始音频
    user_text: str                   # 用户文本

    # LLM 对话相关
    messages: Annotated[...]         # 消息历史（使用 add_messages reducer）
    system_prompt: Optional[str]     # 系统提示词

    # 工具调用相关 (Phase 3 ✅)
    tool_calls: Optional[List[...]]  # 工具调用请求
    tool_results: Optional[List[...]] # 工具执行结果

    # 输出相关
    response_text: str               # LLM 回复文本
    response_chunks: List[str]       # 流式输出块
    tts_audio: Optional[...]         # TTS 音频
    emotion: Optional[str]           # 情感标签

    # 元数据
    session_id: str
    persona: Optional[Dict]
    channel_id: Optional[str]
    # ...
```

#### 1.2 创建图构建器 ✅

**文件**: `src/anima/graph/builder.py`

**内容**:
- `build_graph()` - 构建状态图
- `create_default_graph()` - 创建默认配置的状态图
- `route_input()` - 输入路由函数（音频 → ASR, 文本 → LLM）
- `should_use_tools()` - 工具调用路由函数（Phase 3 ✅）
- `visualize_graph()` - 可视化图结构
- `print_graph_structure()` - 打印图结构

**图结构**:
```
[START]
  |
  +--(音频输入)--> [asr_node]
  |                  |
  +--(文本输入)------+-> [llm_node]
                            |
                   +--------+--------+
                   |                 |
             (有工具调用)      (直接回复)
                   |                 |
               [tool_node]      [tts_node]
                   |                 |
                   +-------+---------+
                           |
                      [emotion_node]
                           |
                      [output_node]
                           |
                         [END]
```

### Phase 2: 实现核心节点 ✅

#### 2.1 ASR 节点 ✅

**文件**: `src/anima/graph/nodes/asr_node.py`

- 接收音频数据 (state["raw_audio"])
- 调用现有 ASR 服务 (service_context.asr_engine)
- 将识别结果写入 state["user_text"]
- 创建 HumanMessage 并追加到 messages

#### 2.2 LLM 节点 ✅

**文件**: `src/anima/graph/nodes/llm_node.py`

- 接收用户文本 (state["user_text"])
- 构建包含人设的 prompt
- 调用现有 LLM 服务的 chat_stream() 方法
- 将结果写入 state["response_text"], state["response_chunks"]
- 创建 AIMessage 并追加到 messages
- **Phase 1 不支持工具调用，Phase 3 支持工具调用 ✅**

#### 2.3 TTS 节点 ✅

**文件**: `src/anima/graph/nodes/tts_node.py`

- 接收 LLM 回复文本 (state["response_text"])
- 调用现有 TTS 服务 (service_context.tts_engine)
- 将合成音频写入 state["tts_audio"]
- TTS 失败不阻断流程（audio 可选）

#### 2.4 情感分析节点 ✅

**文件**: `src/anima/graph/nodes/emotion_node.py`

- 接收 LLM 回复文本 (state["response_text"])
- 调用现有情感分析器 (emotion_analyzer)
- 将情感标签写入 state["emotion"]
- 情感分析失败不阻断流程（默认 neutral）

#### 2.5 输出节点 ✅

**文件**: `src/anima/graph/nodes/output_node.py`

- 接收最终结果 (response_text, tts_audio, emotion)
- 通过 Socket.IO 推送到前端
- 替代现有 EventBus 的分发职责

**Socket.IO 事件**:
- `chat_response` - 文字显示
- `audio_play` - 语音播放
- `expression_change` - Live2D 表情切换
- `control` - 控制信号

#### 2.6 工具节点 ✅

**文件**: `src/anima/graph/nodes/tool_node.py`

- Phase 1/2: 空实现，不执行工具调用
- **Phase 3: 完整实现 ✅**

### 编排器 ✅

**文件**: `src/anima/graph/orchestrator.py`

- `LangGraphOrchestrator` - 封装 LangGraph 执行逻辑
- `LangGraphOrchestratorFactory` - 工厂类，管理实例
- **Phase 3: 支持工具配置和 ChatModel 创建 ✅**

**接口**:
```python
orchestrator = LangGraphOrchestrator(
    service_context=service_context,
    socketio=sio,
    emotion_analyzer=emotion_analyzer,
    enable_tools=True,  # Phase 3 新增
    tools_config=tools_config,  # Phase 3 新增
)

# 文本输入
await orchestrator.process_text(text="你好")

# 音频输入
await orchestrator.process_audio(audio_data=b"...")
```

### Phase 3: Tool Use（工具调用）✅

#### 3.1 工具基类和内置工具 ✅

**文件**: `src/anima/tools/base.py`

**内置工具**:
- `web_search` - 互联网搜索
- `get_weather` - 天气查询
- `read_file` - 文件读取
- `get_current_time` - 当前时间
- `list_directory` - 目录列表
- `calculator` - 数学计算

**功能**:
- `get_builtin_tools()` - 获取所有内置工具
- `get_tools_map()` - 创建工具映射
- `create_tool_registry()` - 创建工具注册表
- `load_tools_from_config()` - 从配置加载工具

#### 3.2 LangChain ChatModel 适配器 ✅

**文件**: `src/anima/services/llm/langchain_adapter.py`

**功能**:
- `LLMChatModelAdapter` - 将现有 LLM 服务包装为 LangChain ChatModel
- `LLMChatModelWithTooling` - 支持工具调用的适配器
- `create_chat_model_from_service()` - 从服务创建 ChatModel

#### 3.3 升级 LLM 节点支持 Tool Use ✅

**文件**: `src/anima/graph/nodes/llm_node.py`

**变更**:
- `_llm_without_tools()` - 无工具调用模式（Phase 1/2）
- `_llm_with_tools()` - 支持工具调用模式（Phase 3）
- 自动检测是否启用工具并选择相应模式
- 解析 `AIMessage.tool_calls` 字段

#### 3.4 实现工具执行节点 ✅

**文件**: `src/anima/graph/nodes/tool_node.py`

**功能**:
- 遍历 `state["tool_calls"]`
- 根据工具名称查找并执行工具
- 将结果封装为 `ToolMessage`
- 错误处理和重试支持

#### 3.5 更新图构建器支持工具 ✅

**文件**: `src/anima/graph/builder.py`

**变更**:
- `build_graph()` 接受 `tools` 和 `tools_map` 参数
- 启用工具时注册 `tool_node`
- 配置 `llm -> tools -> llm` 循环
- 条件路由：`should_use_tools()` 决定下一步

### Phase 4: MCP 协议支持 ✅

#### 4.1 MCP 桥接工具 ✅

**文件**: `src/anima/tools/mcp_bridge.py`

**功能**:
- `MCPServerClient` - MCP 服务器客户端
- `MCPToolManager` - MCP 工具管理器
- `load_mcp_tools()` - 从 MCP 服务器加载工具
- `mcp_tool_to_langchain()` - 将 MCP 工具转换为 LangChain 工具

**支持的传输方式**:
- `stdio` - 标准输入输出（默认）
- `sse` - Server-Sent Events（待完善）

#### 4.2 工具配置系统 ✅

**文件**: `src/anima/tools/config.py`

**功能**:
- `load_tools_config()` - 从 YAML 加载配置
- `validate_tools_config()` - 验证配置有效性
- `_get_default_config()` - 获取默认配置

#### 4.3 配置文件 ✅

**文件**: `config/tools.yaml`

**配置项**:
- `builtin_tools` - 启用的内置工具列表
- `mcp_servers` - MCP 服务器配置
- `tool_settings` - 工具调用设置

### 测试 ✅

**文件**:
- `tests/test_langgraph.py` - LangGraph 基础测试
- `tests/test_tools.py` - 工具系统测试

**运行测试**:
```bash
python tests/test_langgraph.py
python tests/test_tools.py
```

### 文档 ✅

**文件**:
- `docs/TOOLS.md` - 工具系统使用说明

## 待完成阶段

### Phase 5: 增强记忆系统 RAG ✅

- [x] 记忆检索集成到 LLM 节点
- [x] 对话结束后存储记忆
- [x] RAG 检索优化

**实现位置**:
- `src/anima/graph/nodes/llm_node.py` - `_retrieve_memory_context()`
- `src/anima/graph/nodes/output_node.py` - `_store_conversation_to_memory()`

### Phase 6: 集成与清理 ✅

- [x] 在 `socketio_server.py` 中添加 LangGraph 路由
- [x] **删除**模式切换，完全迁移到 LangGraph
- [x] **删除**现有 Adapter 层
- [x] **删除**旧架构代码（pipeline/events/handlers）
- [x] 依赖安装和测试
- [x] 文档更新

**已删除目录**:
- `src/anima/pipeline/` - Pipeline 处理流程
- `src/anima/events/` - EventBus 事件系统
- `src/anima/handlers/` - 事件处理器
- `src/anima/adapters/` - 适配器层
- `src/anima/core/` - 核心抽象层
- `src/anima/services/conversation/` - 旧的对话编排器
- `src/anima/state/` - 旧的状态模块
- `config/features/langgraph.yaml` - 模式切换配置

## 目录结构

```
src/anima/
├── graph/                    # ✅ LangGraph 状态图
│   ├── __init__.py
│   ├── state.py              # 状态定义
│   ├── builder.py            # 图构建器（支持工具）
│   ├── orchestrator.py       # 编排器（支持工具）
│   └── nodes/                # 节点
│       ├── __init__.py
│       ├── asr_node.py       # ASR 节点
│       ├── llm_node.py       # LLM 节点（支持工具）
│       ├── tts_node.py       # TTS 节点
│       ├── emotion_node.py   # 情感节点
│       ├── output_node.py    # 输出节点
│       └── tool_node.py      # 工具节点（✅ 完整实现）
├── tools/                    # ✅ 工具系统
│   ├── __init__.py
│   ├── base.py               # 内置工具
│   ├── config.py             # 配置加载
│   └── mcp_bridge.py         # MCP 桥接
├── services/
│   └── llm/
│       └── langchain_adapter.py  # ✅ LangChain 适配器
├── memory/                   # ✅ 记忆系统（已集成）
├── avatar/                   # ✅ Live2D 表情分析
├── server/                   # ✅ WebSocket 服务器（已迁移）
└── utils/                    # ✅ 工具函数

config/
└── tools.yaml                # ✅ 工具配置（新增）

tests/
├── test_langgraph.py         # LangGraph 测试
└── test_tools.py             # ✅ 工具测试（新增）

docs/
└── TOOLS.md                  # ✅ 工具使用说明（新增）
```

## 使用方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行测试

```bash
# LangGraph 基础测试
python tests/test_langgraph.py

# 工具系统测试
python tests/test_tools.py
```

### 3. 使用编排器（带工具）

```python
from anima.graph import LangGraphOrchestratorFactory
from anima.tools.config import load_tools_config

# 加载工具配置
tools_config = load_tools_config()

# 创建编排器（启用工具）
orchestrator = await LangGraphOrchestratorFactory.create(
    session_id="session_001",
    service_context=service_context,
    socketio=sio,
    emotion_analyzer=emotion_analyzer,
    enable_tools=True,  # 启用工具调用
    tools_config=tools_config,
)

# 处理文本输入（自动调用工具）
result = await orchestrator.process_text(
    text="帮我搜索 Python 教程",
    user_id="user_001",
    user_name="Alice",
)

# 处理音频输入
result = await orchestrator.process_audio(
    audio_data=audio_bytes,
)
```

### 4. 配置工具

编辑 `config/tools.yaml`:

```yaml
# 启用的内置工具
builtin_tools:
  - web_search
  - calculator

# MCP 服务器（可选）
mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
```

## 注意事项

1. **LangGraph 作为唯一架构**: 不再支持 EventBus 架构
2. **工具调用可选**: 通过 `config/tools.yaml` 启用
3. **MCP 可选**: 如果未安装 `mcp` 包，MCP 功能会被跳过
4. **记忆系统自动工作**: 无需额外配置，自动存储和检索
5. **工具安全**: 工具可访问文件系统和网络，请谨慎配置

## 相关文档

- [完整迁移计划](../docs/plans/ADAPTER_MCP_IMPLEMENTATION_PLAN.md)
- [工具系统使用说明](../docs/TOOLS.md)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [项目 CLAUDE.md](../CLAUDE.md)
