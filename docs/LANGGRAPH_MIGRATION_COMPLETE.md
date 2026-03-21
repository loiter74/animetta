# LangGraph 迁移完成

## 概述

Anima 已完全从 EventBus 架构迁移到 LangGraph 状态图架构。

## 已删除的模块

以下旧架构模块已被完全删除：

- ✅ `src/anima/pipeline/` - Pipeline 处理流程
- ✅ `src/anima/events/` - EventBus 事件系统
- ✅ `src/anima/handlers/` - 事件处理器
- ✅ `src/anima/adapters/` - 适配器层
- ✅ `src/anima/core/` - 核心抽象层
- ✅ `src/anima/services/conversation/` - 旧的对话编排器
- ✅ `src/anima/state/` - 旧的状态模块
- ✅ `config/features/langgraph.yaml` - 模式切换配置

## 新架构结构

```
src/anima/
├── graph/                    # LangGraph 状态图
│   ├── state.py              # AgentState 定义
│   ├── builder.py            # 图构建器
│   ├── orchestrator.py       # LangGraphOrchestrator
│   └── nodes/                # 图节点
│       ├── asr_node.py       # ASR 节点
│       ├── llm_node.py       # LLM 节点（带 RAG）
│       ├── tts_node.py       # TTS 节点
│       ├── emotion_node.py   # 情感分析节点
│       ├── output_node.py    # 输出节点（存储记忆）
│       └── tool_node.py      # 工具执行节点
├── tools/                    # 工具系统
│   ├── base.py               # 内置工具
│   ├── config.py             # 配置加载
│   └── mcp_bridge.py         # MCP 桥接
├── services/                 # 服务实现（保留）
│   ├── llm/                  # LLM 服务 + LangChain 适配器
│   ├── asr/                  # ASR 服务
│   ├── tts/                  # TTS 服务
│   ├── vad/                  # VAD 服务
│   └── live2d/               # Live2D 相关
├── memory/                   # 记忆系统（保留 + 增强）
├── avatar/                   # Live2D 表情分析（保留）
├── server/                   # WebSocket 服务器
├── config/                   # 配置系统
├── utils/                    # 工具函数
└── socketio_server.py        # 入口文件
```

## Phase 5 完成情况

### 5.1 记忆 RAG 检索
- **文件**: `src/anima/graph/nodes/llm_node.py`
- **功能**:
  - 从短期记忆获取最近对话
  - 从长期记忆执行混合搜索（向量 70% + BM25 30%）
  - 将记忆上下文注入系统提示词

### 5.2 记忆自动存储
- **文件**: `src/anima/graph/nodes/output_node.py`
- **功能**:
  - 每轮对话结束后自动存储
  - 包含时间戳、情感标签
  - 自动计算重要性分数

## Phase 6 完成情况

### 6.1 LangGraph 作为唯一架构
- **文件**: `src/anima/server/session.py`, `src/anima/server/routes.py`
- 移除了模式切换逻辑
- LangGraph 编排器作为唯一实现

### 6.2 清理旧模块
- 删除所有 EventBus/Pipeline 相关代码
- 删除适配器层
- 删除旧的事件处理器

## 数据流（新架构）

```
用户输入 (文本/音频)
    ↓
[asr_node] 语音识别（音频输入时）
    ↓
[llm_node] LLM 推理（带 RAG 记忆检索）
    ↓
── 条件边 ──→ LLM 决定是否调用工具？
    │                    │
    │ 否（直接回复）      │ 是（需要工具）
    ↓                    ↓
[tts_node]         [tool_node] 执行工具调用
    │                    │
    ↓                    │ 工具结果返回
[emotion_node]           ↓
    ↓                    ↓
[output_node]      回到 [llm_node]（再次推理）
    ↓                    ↓
Socket.IO → 前端渲染 + 存储记忆
```

## 使用方式

### 配置工具

编辑 `config/tools.yaml`:
```yaml
builtin_tools:
  - web_search
  - get_weather
  - read_file
  - calculator

mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]
```

### 启动服务器

```bash
# 启动后端（默认包含 LangGraph）
python -m anima.socketio_server

# 或使用启动脚本
python scripts/start.py
```

## 注意事项

1. **无需切换模式**：系统现在直接使用 LangGraph 架构
2. **工具调用可选**：通过配置文件控制是否启用
3. **前端兼容**：Socket.IO 事件格式保持不变
4. **记忆系统**：自动存储和检索，无需手动配置

## 相关文档

- [完整迁移计划](./plans/LANGCHAIN_REFACTOR.md)
- [工具使用说明](./TOOLS.md)
