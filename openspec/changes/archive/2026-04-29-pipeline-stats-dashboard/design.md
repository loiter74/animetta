## Context

Anima 使用 LangGraph 状态图编排对话流程：ASR → LLM(+RAG) → Tool? → TTS → Emotion → Output。每个节点是独立的 `async def node(state, config)` 函数，通过 `graph.ainvoke()` 执行。

当前已有 `ObservabilityManager`（`observability.py`）集成 LangFuse/LangSmith，通过 `BaseCallbackHandler` 接口采集数据发往云端。但缺少本地轻量级的结构化统计，无法在不连外部服务的情况下查看链路性能。

现有后端是纯 Socket.IO ASGI 应用（`socketio.ASGIApp`），无 HTTP API 路由。前端是 Electron + vanilla JS。

## Goals / Non-Goals

**Goals:**
- 零侵入采集 LangGraph 各节点执行耗时、状态和输入输出摘要
- 提供 HTTP API 和 Web Dashboard 展示统计数据
- 使用 OpenTelemetry 的 Trace/Span 模型，支持未来多 Agent 层级扩展
- 数据持久化到本地 SQLite，零外部依赖

**Non-Goals:**
- 不替代 LangFuse/LangSmith 云端 tracing
- 不做实时流式监控（用 5s 轮询足够）
- 不引入时序数据库或 Grafana
- 不嵌入 Electron 桌面应用（独立 Web 页面）

## Decisions

### 1. 采集方式：LangChain Callback Handler

**选择：** 继承 `BaseCallbackHandler`，监听 `on_chain_start` / `on_chain_end` / `on_chain_error`。

**替代方案：**
- 节点装饰器：需要修改每个节点文件，侵入性强
- `graph.astream()` 流式拦截：只能拿到完成时刻，精度差

**理由：** 与现有 LangFuse 集成同一模式（`observability.py` 中 `CallbackHandler`），关注点分离，不动业务代码。

### 2. 数据模型：Trace/Span（OpenTelemetry 风格）

**选择：** 一次请求 = 一个 Trace，一个节点 = 一个 Span。`spans.parent_span_id` 预留为多 Agent 准备。

**理由：** 面试时能解释分布式追踪模型，且未来零改动适配多 Agent。

### 3. 存储：SQLite + aiosqlite

**选择：** 两张表（traces, spans），索引覆盖查询模式。

**替代方案：**
- 纯内存：重启丢失
- Prometheus：引入重依赖

**理由：** 项目已用 SQLite（memory 系统），风格一致，零运维。

### 4. HTTP 路由：Starlette 挂载

**选择：** 在 `websocket.py` 中用 Starlette 包装 `socketio.ASGIApp`，添加 `/api/stats/*` 路由和 `/stats/` 静态页面。

**理由：** Starlette 是 uvicorn 的底层框架（已安装），无需引入新依赖。`socketio.ASGIApp` 的未匹配路径会 fallback 到 Starlette 路由。

### 5. 前端：vanilla JS + Chart.js

**选择：** 独立 HTML/CSS/JS 页面，Chart.js 画柱状图，5s 轮询刷新。

**理由：** 和项目前端风格一致（无 React），Chart.js 轻量，面试 demo 方便。

## Risks / Trade-offs

- **Callback 时序**：LangGraph 的 callback 在异步环境中触发，需要用 `asyncio.ensure_future` 而非 `await`，避免阻塞主流程 → 回调写入失败不影响业务，仅 log warning
- **SQLite 并发写入**：aiosqlite 单连接写入，高并发时可能排队 → 对本项目场景（单用户 VTuber）完全足够
- **节点名识别**：`on_chain_start` 的 `name` 字段来自 LangGraph 内部命名，需要维护已知节点名列表过滤 → 后续节点增删时更新列表
