## Why

Anima 的 LangGraph 调用链路（ASR → LLM → TTS → Emotion → Output）目前缺少结构化的性能数据采集。开发时只能靠日志判断延迟，无法量化各节点耗时、成功率，也无法回溯某次请求的完整链路。需要一个全链路可观测性面板来支撑开发调试、性能优化和面试展示。

## What Changes

- 新增 LangGraph Callback Handler，自动采集每个节点的执行耗时、状态和输入输出摘要，不侵入现有节点代码
- 新增 SQLite 存储层，持久化 Trace/Span 数据（OpenTelemetry 模型）
- 新增 HTTP API 暴露统计数据（总览、节点统计、链路列表、链路详情）
- 新增独立 Web Dashboard 页面，展示 KPI 卡片、节点耗时柱状图、最近请求列表和链路详情
- 在现有 Socket.IO ASGI 应用上挂载 Starlette 路由，提供 API 和静态页面服务
- spans 表预留 `parent_span_id` 字段，为未来多 Agent 架构做准备

## Capabilities

### New Capabilities
- `pipeline-tracing`: 通过 LangChain BaseCallbackHandler 采集 LangGraph 节点生命周期事件（on_chain_start/end/error），生成 Trace 和 Span 数据
- `stats-storage`: SQLite 持久化存储 Trace/Span 数据，支持统计查询（总览、节点聚合、分页列表、链路详情）
- `stats-api`: Starlette HTTP API 路由，暴露统计数据给前端 Dashboard（/api/stats/overview, /nodes, /traces, /traces/{id}）
- `stats-dashboard`: 独立 Web 页面（vanilla JS + Chart.js），展示 KPI 卡片、节点耗时柱状图、请求列表和链路详情模态框

### Modified Capabilities

## Impact

- `src/anima/orchestration/graph/orchestrator.py`: 注入 StatsCallbackHandler 到 LangGraph callbacks
- `src/anima/orchestration/server/websocket.py`: 替换纯 Socket.IO ASGI 为 Starlette 路由包装
- `.gitignore`: 添加 data/stats.db
- `requirements.txt`: 可能添加 aiosqlite 依赖
- 新增目录 `frontend/stats/`: Dashboard 前端文件
