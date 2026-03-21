# Anima 架构迁移计划：EventBus → LangGraph

## 项目概述

**项目名称**: Anima-LLM-Vtuber  
**迁移目标**: 将核心对话编排层从自定义 EventBus 架构迁移到 LangGraph 状态图架构  
**迁移目的**: 引入 Tool Use / Agent 能力，支持 MCP 协议，对齐行业主流 AI Agent 技术栈  
**预计工期**: 6-8 周

---

## 当前架构

### 技术栈
- **后端**: Python, FastAPI, Socket.IO
- **前端**: Electron, 原生 JS, pixi-live2d-display
- **AI 服务**: GLM, OpenAI, FasterWhisper, Silero VAD, Chroma
- **向量数据库**: Chroma（用于记忆系统）

### 当前目录结构
```
src/anima/
├── socketio_server.py    # 主服务器入口
├── service_context.py    # 服务容器管理
├── config/               # 配置系统
│   ├── core/registry.py  # 服务注册表（ProviderRegistry 装饰器模式）
│   └── providers/        # 各服务商配置类（LLM/ASR/TTS）
├── adapters/             # 通道适配器层
├── services/             # 服务实现
│   ├── llm/              # LLM 服务（GLM, OpenAI, Ollama, LoRA）
│   ├── asr/              # 语音识别（FasterWhisper, GLM, OpenAI）
│   ├── tts/              # 语音合成（Edge TTS, GLM, OpenAI, ChatTTS）
│   └── vad/              # 语音活动检测（Silero VAD）
├── pipeline/             # 数据处理管道（InputPipeline, OutputPipeline）
├── events/               # 事件驱动架构（EventBus）
├── handlers/             # 事件处理器
├── memory/               # 对话记忆系统（基于 Chroma）
└── avatar/               # Live2D 表情分析
```

### 当前数据流
```
用户输入 (文本/音频)
    ↓
InputPipeline (ASR 语音识别 → 文本清洗)
    ↓
Agent (LLM 流式对话，无 Tool Use)
    ↓
OutputPipeline (句子分割 → TTS 合成 → 情感提取)
    ↓
EventBus (按优先级分发事件)
    ↓
前端渲染 (文字显示 + 语音播放 + Live2D 动作)
```

### 当前编排机制
- **EventBus** 负责模块间解耦通信
- **Pipeline** 负责线性的输入/输出数据处理
- **无条件分支**: LLM 只能直接回复，不能决定是否调用工具
- **无循环**: 不支持 "调用工具 → 获取结果 → 再次推理" 的 Agent 循环

---

## 目标架构

### 迁移后目录结构
```
src/anima/
├── socketio_server.py    # 主服务器入口（保留，微调）
├── service_context.py    # 服务容器管理（保留，扩展）
├── config/               # 配置系统（保留）
│   ├── core/registry.py  # 服务注册表（保留）
│   └── providers/        # 服务商配置类（保留 + 新增 tools 配置）
├── adapters/             # 通道适配器层（保留）
├── services/             # 服务实现（全部保留）
│   ├── llm/              # 保留
│   ├── asr/              # 保留
│   ├── tts/              # 保留
│   └── vad/              # 保留
├── graph/                # 【新增】LangGraph 状态图
│   ├── state.py          # 全局状态定义（AgentState）
│   ├── builder.py        # 图构建器（创建 StateGraph）
│   └── nodes/            # 图节点
│       ├── asr_node.py       # 语音识别节点
│       ├── llm_node.py       # LLM 推理节点
│       ├── tool_node.py      # 工具执行节点
│       ├── tts_node.py       # 语音合成节点
│       ├── emotion_node.py   # 情感分析节点
│       └── output_node.py    # 输出分发节点
├── tools/                # 【新增】Tool Use 工具定义
│   ├── base.py           # 工具基类
│   ├── web_search.py     # 网页搜索工具
│   ├── weather.py        # 天气查询工具
│   ├── file_reader.py    # 文件读取工具
│   └── mcp_bridge.py     # MCP 协议桥接
├── memory/               # 对话记忆系统（保留 + 增强 RAG）
└── avatar/               # Live2D 表情分析（保留）
```

### 删除的模块
```
├── pipeline/             # 【删除】被 LangGraph 节点替代
├── events/               # 【删除】被 LangGraph 状态流转替代
├── handlers/             # 【删除】被 LangGraph 节点替代
```

### 目标数据流（LangGraph 状态图）
```
用户输入 (文本/音频)
    ↓
[asr_node] 语音识别（音频输入时）
    ↓
[llm_node] LLM 推理（带 tool schemas）
    ↓
── 条件边 ──→ LLM 决定是否调用工具？
    │                    │
    │ 否（直接回复）      │ 是（需要工具）
    ↓                    ↓
[tts_node]         [tool_node] 执行工具调用
    ↓                    │
[emotion_node]           │ 工具结果返回
    ↓                    ↓
[output_node]      回到 [llm_node]（带工具结果再次推理）
    ↓
Socket.IO → 前端渲染
```

---

## 迁移步骤

### Phase 0: 环境准备（第 1 天）

#### 0.1 安装依赖
```bash
pip install langgraph langchain langchain-core langchain-openai langchain-community
```

#### 0.2 在 requirements.txt 中添加
```
langgraph>=0.2.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-openai>=0.2.0
langchain-community>=0.3.0
```

#### 0.3 确认现有测试通过
在开始迁移前，确保当前 EventBus 架构的所有功能正常运行，记录一份功能基线清单：
- [ ] 文本输入 → LLM 回复 → 前端显示
- [ ] 语音输入 → ASR → LLM → TTS → 语音播放
- [ ] Live2D 表情根据对话内容变化
- [ ] 流式输出正常工作
- [ ] 记忆系统正常存储和检索
- [ ] 多模型切换正常（GLM/OpenAI/Ollama）

---

### Phase 1: 定义 LangGraph 状态（第 1 周）

#### 1.1 创建全局状态定义

**文件**: `src/anima/graph/state.py`

**设计要求**:
- 使用 `TypedDict` 定义 `AgentState`，包含整个对话流程中需要传递的所有数据
- 状态应覆盖：用户输入、ASR 结果、LLM 消息历史、工具调用请求、工具执行结果、TTS 音频、情感标签、输出数据
- 使用 LangGraph 的 `Annotated` 类型和 reducer 函数处理消息列表的追加

**状态字段设计**:
```python
from typing import TypedDict, Annotated, Sequence, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 输入相关
    input_type: str                              # "text" 或 "audio"
    raw_audio: Optional[bytes]                   # 原始音频数据
    user_text: str                               # 用户文本（直接输入或 ASR 结果）
    
    # LLM 对话相关
    messages: Annotated[list[BaseMessage], add_messages]  # 完整消息历史
    
    # 工具调用相关
    tool_calls: Optional[list[dict]]             # LLM 请求的工具调用
    tool_results: Optional[list[dict]]           # 工具执行结果
    
    # 输出相关
    response_text: str                           # LLM 最终回复文本
    response_chunks: list[str]                   # 流式输出的文本块
    tts_audio: Optional[bytes]                   # TTS 合成的音频
    emotion: str                                 # 情感标签（用于 Live2D 表情）
    
    # 元数据
    session_id: str                              # 会话 ID
    persona: dict                                # 角色人设配置
```

**约束**:
- `messages` 字段必须使用 `add_messages` reducer，确保新消息追加而非覆盖
- 所有 Optional 字段应有合理的默认处理逻辑，节点不应因上游未赋值而崩溃

---

#### 1.2 创建图构建器

**文件**: `src/anima/graph/builder.py`

**设计要求**:
- 创建一个 `build_graph()` 函数，接收 `service_context`（现有服务容器）作为参数
- 使用 `StateGraph(AgentState)` 构建状态图
- 在此阶段只注册节点和边，不实现节点内部逻辑（节点实现在后续 Phase）
- 图结构如下：

```python
from langgraph.graph import StateGraph, END

def build_graph(service_context) -> StateGraph:
    graph = StateGraph(AgentState)
    
    # 注册节点
    graph.add_node("asr", asr_node)
    graph.add_node("llm", llm_node)
    graph.add_node("tools", tool_node)
    graph.add_node("tts", tts_node)
    graph.add_node("emotion", emotion_node)
    graph.add_node("output", output_node)
    
    # 设置入口点（条件入口：根据输入类型决定）
    graph.set_conditional_entry_point(
        route_input,  # 路由函数：audio → asr, text → llm
        {"asr": "asr", "llm": "llm"}
    )
    
    # ASR → LLM
    graph.add_edge("asr", "llm")
    
    # LLM → 条件分支（是否调用工具）
    graph.add_conditional_edges(
        "llm",
        should_use_tools,  # 路由函数：检查 state["tool_calls"]
        {"tools": "tools", "tts": "tts"}
    )
    
    # 工具执行 → 回到 LLM（Agent 循环）
    graph.add_edge("tools", "llm")
    
    # TTS → 情感分析 → 输出
    graph.add_edge("tts", "emotion")
    graph.add_edge("emotion", "output")
    graph.add_edge("output", END)
    
    return graph.compile()
```

**路由函数**:
```python
def route_input(state: AgentState) -> str:
    """根据输入类型决定起始节点"""
    if state["input_type"] == "audio" and state.get("raw_audio"):
        return "asr"
    return "llm"

def should_use_tools(state: AgentState) -> str:
    """检查 LLM 是否请求了工具调用"""
    if state.get("tool_calls"):
        return "tools"
    return "tts"
```

---

### Phase 2: 实现核心节点（第 2-3 周）

**核心原则**: 每个节点内部调用现有 `services/` 中的服务实现，不重写业务逻辑。节点只负责：读取状态 → 调用服务 → 写回状态。

#### 2.1 ASR 节点

**文件**: `src/anima/graph/nodes/asr_node.py`

**职责**: 接收音频数据，调用现有 ASR 服务，将识别结果写入 `state["user_text"]`

**实现要求**:
- 从 `service_context` 获取当前配置的 ASR 服务实例
- 调用现有 `services/asr/` 下的服务（FasterWhisper/GLM/OpenAI）
- 不要重写 ASR 逻辑，直接复用现有服务

```python
async def asr_node(state: AgentState, config: dict) -> dict:
    """
    语音识别节点
    
    输入: state["raw_audio"] (bytes)
    输出: state["user_text"] (str)
    
    调用现有服务: service_context.asr_service
    """
    service_context = config["configurable"]["service_context"]
    asr_service = service_context.asr_service
    
    text = await asr_service.recognize(state["raw_audio"])
    
    return {"user_text": text}
```

#### 2.2 LLM 节点

**文件**: `src/anima/graph/nodes/llm_node.py`

**职责**: 
- 接收用户文本，构建 prompt（包含角色人设 + 对话历史 + 工具 schemas）
- 调用 LLM 获取回复
- 解析回复，判断是普通文本回复还是工具调用请求
- 支持流式输出

**实现要求**:
- 第一阶段：复用现有 `services/llm/` 的服务，通过 `chat_stream()` 获取流式回复
- 第二阶段（Phase 3 Tool Use）：切换为 LangChain 的 `ChatModel.bind_tools()` 方式，让 LLM 能返回 tool_calls
- 将角色人设（persona）注入 system prompt
- 从 memory 系统检索相关上下文（RAG，Phase 4 增强）

```python
async def llm_node(state: AgentState, config: dict) -> dict:
    """
    LLM 推理节点
    
    输入: state["user_text"], state["messages"], state["persona"]
    输出: state["messages"]（追加 AI 回复）, state["response_text"], 
          state["tool_calls"]（如有）, state["response_chunks"]（流式块）
    
    Phase 1: 直接调用现有 LLM 服务（无 Tool Use）
    Phase 3: 使用 ChatModel.bind_tools() 支持工具调用
    """
    # Phase 1 实现（无 Tool Use，保持现有行为）
    service_context = config["configurable"]["service_context"]
    llm_service = service_context.llm_service
    
    # 构建包含人设的 system prompt
    persona = state.get("persona", {})
    
    # 调用现有 LLM 流式接口
    chunks = []
    async for chunk in llm_service.chat_stream(
        text=state["user_text"],
        conversation_history=state.get("messages", [])
    ):
        chunks.append(chunk)
    
    response_text = "".join(chunks)
    
    return {
        "response_text": response_text,
        "response_chunks": chunks,
        "messages": [AIMessage(content=response_text)],
        "tool_calls": None  # Phase 1 不调用工具
    }
```

#### 2.3 TTS 节点

**文件**: `src/anima/graph/nodes/tts_node.py`

**职责**: 将 LLM 回复文本转为语音

**实现要求**:
- 复用现有 `services/tts/` 的服务
- 支持流式 TTS（按句子分割后逐句合成）

```python
async def tts_node(state: AgentState, config: dict) -> dict:
    """
    语音合成节点
    
    输入: state["response_text"]
    输出: state["tts_audio"] (bytes)
    
    调用现有服务: service_context.tts_service
    """
    service_context = config["configurable"]["service_context"]
    tts_service = service_context.tts_service
    
    audio = await tts_service.synthesize(state["response_text"])
    
    return {"tts_audio": audio}
```

#### 2.4 情感分析节点

**文件**: `src/anima/graph/nodes/emotion_node.py`

**职责**: 分析 LLM 回复的情感，生成 Live2D 表情标签

**实现要求**:
- 复用现有 `avatar/` 模块的情感分析逻辑

```python
async def emotion_node(state: AgentState, config: dict) -> dict:
    """
    情感分析节点
    
    输入: state["response_text"]
    输出: state["emotion"] (str: "happy", "sad", "angry", "neutral" 等)
    
    调用现有模块: avatar.emotion_analyzer
    """
    service_context = config["configurable"]["service_context"]
    emotion = await service_context.emotion_analyzer.analyze(state["response_text"])
    
    return {"emotion": emotion}
```

#### 2.5 输出节点

**文件**: `src/anima/graph/nodes/output_node.py`

**职责**: 将最终结果通过 Socket.IO 推送到前端

**实现要求**:
- 替代现有 EventBus 的分发职责
- 通过 Socket.IO 发送：文本回复、音频数据、情感/表情指令

```python
async def output_node(state: AgentState, config: dict) -> dict:
    """
    输出分发节点（替代 EventBus）
    
    输入: state["response_text"], state["tts_audio"], 
          state["emotion"], state["response_chunks"]
    输出: 无状态更新（副作用：通过 Socket.IO 推送到前端）
    
    Socket.IO 事件:
    - "chat_response": {text, chunks}    → 文字显示
    - "audio_play": {audio}              → 语音播放
    - "expression_change": {emotion}     → Live2D 表情切换
    """
    sio = config["configurable"]["socketio"]
    session_id = state["session_id"]
    
    await sio.emit("chat_response", {
        "text": state["response_text"],
        "chunks": state["response_chunks"]
    }, room=session_id)
    
    if state.get("tts_audio"):
        await sio.emit("audio_play", {
            "audio": state["tts_audio"]
        }, room=session_id)
    
    await sio.emit("expression_change", {
        "emotion": state["emotion"]
    }, room=session_id)
    
    return {}
```

---

### Phase 3: 实现 Tool Use（第 4-5 周）

#### 3.1 定义工具基类和工具集

**文件**: `src/anima/tools/base.py`

**设计要求**:
- 使用 LangChain 的 `@tool` 装饰器定义工具
- 每个工具有清晰的名称、描述、参数 schema
- 工具应为 async 函数

```python
from langchain_core.tools import tool

@tool
async def web_search(query: str) -> str:
    """搜索互联网获取实时信息。当用户询问你不确定的事实、最新新闻、或需要实时数据时使用。
    
    Args:
        query: 搜索关键词
    """
    # 实现搜索逻辑
    pass

@tool  
async def get_weather(city: str) -> str:
    """查询指定城市的当前天气信息。
    
    Args:
        city: 城市名称（如 "北京", "上海"）
    """
    # 实现天气查询
    pass

@tool
async def read_file(file_path: str) -> str:
    """读取用户本地文件的内容。
    
    Args:
        file_path: 文件路径
    """
    # 实现文件读取
    pass
```

#### 3.2 升级 LLM 节点支持 Tool Use

**文件**: 修改 `src/anima/graph/nodes/llm_node.py`

**修改要求**:
- 将现有 LLM 服务包装为 LangChain 的 `BaseChatModel`，或直接使用 `langchain-openai` / `langchain-community` 的现成模型
- 使用 `model.bind_tools(tools)` 绑定工具
- 解析返回的 `AIMessage.tool_calls` 字段

```python
async def llm_node(state: AgentState, config: dict) -> dict:
    """
    LLM 推理节点（Phase 3: 支持 Tool Use）
    
    变更: 使用 LangChain ChatModel + bind_tools 替代直接调用现有服务
    
    逻辑:
    1. 构建 messages 列表（system prompt + 历史 + 用户输入）
    2. 调用 model.bind_tools(tools).ainvoke(messages)
    3. 如果返回 tool_calls → 写入 state["tool_calls"]
    4. 如果返回纯文本 → 写入 state["response_text"]
    """
    tools = config["configurable"]["tools"]
    model = config["configurable"]["chat_model"]
    
    model_with_tools = model.bind_tools(tools)
    
    response = await model_with_tools.ainvoke(state["messages"])
    
    if response.tool_calls:
        return {
            "messages": [response],
            "tool_calls": response.tool_calls,
            "response_text": "",
        }
    else:
        return {
            "messages": [response],
            "tool_calls": None,
            "response_text": response.content,
            "response_chunks": [response.content],
        }
```

#### 3.3 实现工具执行节点

**文件**: `src/anima/graph/nodes/tool_node.py`

**设计要求**:
- 使用 LangGraph 内置的 `ToolNode` 或自行实现
- 接收 `state["tool_calls"]`，执行对应工具，将结果作为 `ToolMessage` 追加到 messages

```python
from langgraph.prebuilt import ToolNode

# 方式一：使用 LangGraph 内置 ToolNode（推荐）
tool_node = ToolNode(tools=[web_search, get_weather, read_file])

# 方式二：自定义实现（需要更细粒度控制时）
async def tool_node(state: AgentState, config: dict) -> dict:
    """
    工具执行节点
    
    输入: state["tool_calls"] (list[dict])
    输出: state["messages"]（追加 ToolMessage）, state["tool_results"]
    
    流程:
    1. 遍历 tool_calls
    2. 根据工具名称找到对应函数
    3. 执行工具并收集结果
    4. 将结果封装为 ToolMessage 追加到 messages
    """
    tools_map = config["configurable"]["tools_map"]
    results = []
    tool_messages = []
    
    for tool_call in state["tool_calls"]:
        tool_fn = tools_map[tool_call["name"]]
        result = await tool_fn.ainvoke(tool_call["args"])
        results.append(result)
        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )
    
    return {
        "messages": tool_messages,
        "tool_results": results,
        "tool_calls": None,  # 清除，避免再次进入工具节点
    }
```

#### 3.4 更新图构建器

**文件**: 修改 `src/anima/graph/builder.py`

**修改要求**:
- 在 `build_graph()` 中传入 tools 列表
- 将工具绑定到 LLM 节点和工具节点

---

### Phase 4: 接入 MCP 协议（第 5-6 周）

#### 4.1 MCP 桥接工具

**文件**: `src/anima/tools/mcp_bridge.py`

**设计要求**:
- 创建一个 MCP 客户端，能连接外部 MCP 服务器
- 将 MCP 服务器暴露的工具动态注册为 LangChain 工具
- 这样任何 MCP 兼容的工具服务器都能被 Anima 的 Agent 调用

```python
"""
MCP 桥接模块

职责:
1. 连接 MCP 服务器（通过 stdio 或 HTTP SSE）
2. 发现服务器提供的工具列表
3. 将每个 MCP 工具转换为 LangChain Tool 对象
4. 注入到 LangGraph 的工具列表中

依赖: mcp (pip install mcp)

配置示例 (config/tools.yaml):
  mcp_servers:
    - name: "file-system"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"]
    - name: "web-search"  
      url: "http://localhost:8080/mcp"
"""
```

#### 4.2 MCP 配置

**文件**: `config/tools.yaml`（新增）

```yaml
# 内置工具
builtin_tools:
  - web_search
  - get_weather
  - read_file

# MCP 服务器
mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
  
  - name: "web-search"
    transport: "sse"
    url: "http://localhost:8080/mcp"
```

---

### Phase 5: 增强记忆系统 RAG（第 6-7 周）

#### 5.1 记忆检索集成到 LLM 节点

**修改文件**: `src/anima/graph/nodes/llm_node.py`

**修改要求**:
- 在 LLM 推理前，从 Chroma 中检索与当前用户输入相关的历史对话和知识
- 将检索结果注入 system prompt 的上下文中
- 实现记忆的存储：每轮对话结束后，将新的对话存入 Chroma

```python
# 在 llm_node 中增加 RAG 检索步骤
async def llm_node(state: AgentState, config: dict) -> dict:
    """
    增强: 在调用 LLM 前执行 RAG 检索
    
    新增步骤:
    1. 用 user_text 在 Chroma 中检索 top-k 相关记忆
    2. 将检索结果格式化后注入 system prompt
    3. 调用 LLM（其余逻辑不变）
    """
    memory_service = config["configurable"]["memory_service"]
    
    # 检索相关记忆
    relevant_memories = await memory_service.search(
        query=state["user_text"],
        top_k=5
    )
    
    # 注入到 system prompt
    memory_context = format_memories(relevant_memories)
    # ... 继续原有 LLM 调用逻辑
```

#### 5.2 对话结束后存储记忆

**修改文件**: `src/anima/graph/nodes/output_node.py`

**修改要求**:
- 在输出节点中，将本轮对话（用户输入 + AI 回复）存入 Chroma
- 包含时间戳和会话 ID 元数据

---

### Phase 6: 集成与清理（第 7-8 周）

#### 6.1 修改主入口

**修改文件**: `src/anima/socketio_server.py`

**修改要求**:
- 在服务器启动时调用 `build_graph()` 构建 LangGraph 实例
- 将 Socket.IO 事件处理器中的 Pipeline/EventBus 调用替换为 `graph.ainvoke(state)`
- 传递 `service_context` 和其他依赖通过 LangGraph 的 `config` 参数

```python
# 伪代码示例
graph = build_graph(service_context)

@sio.on("user_message")
async def handle_message(sid, data):
    initial_state = {
        "input_type": data.get("type", "text"),
        "user_text": data.get("text", ""),
        "raw_audio": data.get("audio"),
        "session_id": sid,
        "persona": service_context.current_persona,
        "messages": get_session_history(sid),
    }
    
    config = {
        "configurable": {
            "service_context": service_context,
            "socketio": sio,
            "tools": tool_list,
            "tools_map": tools_map,
            "chat_model": chat_model,
            "memory_service": memory_service,
        }
    }
    
    await graph.ainvoke(initial_state, config=config)
```

#### 6.2 删除旧模块
- 删除 `src/anima/pipeline/` 目录
- 删除 `src/anima/events/` 目录
- 删除 `src/anima/handlers/` 目录
- 清理 `service_context.py` 中对旧模块的引用

#### 6.3 更新配置系统

**修改文件**: `config/config.yaml`

```yaml
services:
  agent: glm              # LLM 服务商
  asr: faster_whisper     # ASR 服务商
  tts: edge               # TTS 服务商

# 新增: 工具配置
tools:
  builtin:
    - web_search
    - get_weather
    - read_file
  mcp_servers:
    - name: "filesystem"
      transport: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
```

#### 6.4 功能回归测试
对照 Phase 0 的功能基线清单，逐项验证：
- [ ] 文本输入 → LLM 回复 → 前端显示
- [ ] 语音输入 → ASR → LLM → TTS → 语音播放
- [ ] Live2D 表情根据对话内容变化
- [ ] 流式输出正常工作
- [ ] 记忆系统正常存储和检索（增强 RAG）
- [ ] 多模型切换正常
- [ ] **【新增】** Tool Use: 用户请求时能调用工具获取信息
- [ ] **【新增】** MCP: 能连接外部 MCP 服务器并使用其工具
- [ ] **【新增】** Agent 循环: 工具结果能反馈给 LLM 再次推理

---

## 迁移风险与应对

| 风险 | 影响 | 应对方案 |
|------|------|----------|
| 现有 LLM 服务接口与 LangChain ChatModel 不兼容 | Phase 2-3 延期 | 为每个现有 LLM 服务编写 LangChain Adapter 包装类 |
| 流式输出在 LangGraph 中实现复杂度高 | Phase 2 延期 | 先实现非流式版本，确保核心流程跑通，再迭代流式支持 |
| MCP 服务器连接不稳定 | Phase 4 延期 | MCP 作为可选功能，内置工具优先保证可用 |
| 前端 Socket.IO 事件格式变更 | 前端需要适配 | 保持现有 Socket.IO 事件名称和数据格式不变，仅后端替换 |

---

## 关键约束

1. **前端不改动**: 迁移仅涉及后端架构，前端 Electron 应用、Socket.IO 事件名称和数据格式保持不变
2. **服务实现不重写**: `services/` 目录下的 LLM/ASR/TTS/VAD 实现全部保留复用
3. **配置系统兼容**: 现有 `config/config.yaml` 和 `config/personas/` 的格式保持向后兼容
4. **渐进式迁移**: 每个 Phase 结束后都应该是一个可运行的状态，不能出现"拆了旧的但新的还没装好"的情况