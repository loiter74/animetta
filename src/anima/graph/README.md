# Anima - EventBus → LangGraph 架构迁移

## Phase 1 & Phase 2 已完成 ✅

本项目已完成从自定义 EventBus 架构到 LangGraph 状态图架构的 Phase 1 和 Phase 2 迁移。

### 已完成工作

#### Phase 1: LangGraph 状态定义
- ✅ `state.py` - 定义 AgentState 状态结构
- ✅ `builder.py` - 构建状态图和路由逻辑

#### Phase 2: 核心节点实现
- ✅ `asr_node.py` - 语音识别节点
- ✅ `llm_node.py` - LLM 推理节点
- ✅ `tts_node.py` - 语音合成节点
- ✅ `emotion_node.py` - 情感分析节点
- ✅ `output_node.py` - 输出分发节点

#### 额外完成
- ✅ `orchestrator.py` - 编排器，封装 LangGraph 执行逻辑
- ✅ `tool_node.py` - 工具节点占位符（Phase 3 实现）
- ✅ `test_langgraph.py` - 完整的测试套件

### 目录结构

```
src/anima/graph/
├── __init__.py          # 模块导出
├── state.py             # 状态定义
├── builder.py           # 图构建器
├── orchestrator.py      # 编排器
└── nodes/               # 节点模块
    ├── __init__.py
    ├── asr_node.py
    ├── llm_node.py
    ├── tts_node.py
    ├── emotion_node.py
    ├── output_node.py
    └── tool_node.py     # 占位符
```

### 快速开始

1. **安装依赖**（已更新 requirements.txt）:
   ```bash
   pip install langgraph>=0.2.0 langchain>=0.3.0
   ```

2. **运行测试**:
   ```bash
   python tests/test_langgraph.py
   ```

3. **使用编排器**:
   ```python
   from anima.graph import LangGraphOrchestratorFactory

   orchestrator = await LangGraphOrchestratorFactory.create(
       session_id="session_001",
       service_context=service_context,
       socketio=sio,
       emotion_analyzer=emotion_analyzer,
   )

   # 处理文本
   await orchestrator.process_text(text="你好")

   # 处理音频
   await orchestrator.process_audio(audio_data=b"...")
   ```

### 图结构

```
[START]
  |
  +--(音频)--> [asr_node] --+
  |                         |
  +--(文本)----------------+--> [llm_node]
                                     |
                                [tts_node]
                                     |
                              [emotion_node]
                                     |
                               [output_node]
                                     |
                                    [END]
```

### 下一步

- **Phase 3**: 集成 Tool Use（工具调用）
- **Phase 4**: 集成 MCP 协议
- **集成**: 将 LangGraph 集成到现有 socketio_server.py

### 详细文档

参见 [LANGGRAPH_MIGRATION_PROGRESS.md](../../docs/LANGGRAPH_MIGRATION_PROGRESS.md)
