## Context

Anima v2.0 基于 LangGraph 状态机，后端 FastAPI + Socket.IO。已有 OpenTelemetry 链路追踪骨架：`TracingProxy` 自动为 LLM/ASR/TTS/VAD 服务调用创建 OTel span，`StatsSpanExporter` 将 span 写入 SQLite StatsStore，`StatsCallbackHandler` 通过 LangChain 回调捕获节点耗时。`config/observability.yaml` 配置了 LangSmith + LangFuse + tracing 参数，但 **没有 OTLP 导出**、**没有任何 Prometheus 指标**、**LLM token 用量被丢弃**。

目标是把这套骨架扩展为端到端可观测性闭环，全本地化部署（单机 docker-compose），不引入 SaaS。

## Goals / Non-Goals

**Goals:**
- 一次对话的全链路 trace 能在 Grafana Tempo 中可视化（7 个 LangGraph 节点 span + 服务调用 span）
- 20+ 核心业务指标通过 OTel Metrics API 埋点，经 OTel Collector → Prometheus 可查询
- 4 张 Grafana dashboard 覆盖概览、Pipeline、RAG、成本
- 5 条关键告警通过 Discord/Slack webhook 通知
- 一键启动：`docker-compose -f observability/docker-compose.yml up -d`

**Non-Goals:**
- 不引入 Datadog / Honeycomb / NewRelic 等 SaaS
- 不重写已有 OTel SDK 埋点（TracingProxy、StatsSpanExporter 保留）
- 不做日志聚合（loguru 已够用，不上 Loki）
- 不做用户行为分析
- 不在本 PR 中突击补测试覆盖率（保持与现有 ~21% 一致）

## Decisions

### 1. 双写导出：StatsSpanExporter + OTLPSpanExporter

**选择**：在现有 `SimpleSpanProcessor(StatsSpanExporter)` 基础上，新增 `BatchSpanProcessor(OTLPSpanExporter)`，两个 exporter 并行工作。

**替代方案**：替换式（只保留 OTLP）——会破坏现有 StatsStore + stats API + 前端统计面板，且违反"复用现有代码"原则。

**理由**：StatsStore SQLite 是 Anima 内置统计面板的数据源（`/stats` 路由），OTLP 是 Grafana/Tempo 的数据源。双写确保两边都不受影响。

### 2. OpenTelemetry Metrics API（非 prometheus-client）

**选择**：使用 `opentelemetry-api` 的 `metrics` 模块（`Meter` → `Counter`/`Histogram`/`Gauge`），通过 OTel Collector 的 `prometheus` exporter 暴露 `/metrics` 端点。

**替代方案**：直接用 `prometheus-client` 库——更简单，但会引入第二套遥测 SDK，与现有 OTel 投资割裂。

**理由**：Brief 明确要求 "OpenTelemetry Metrics API，不要用 prometheus-client 直连"。OTel Collector 统一处理 trace + metrics 的导出管道，架构更一致。`opentelemetry-api` 已在 `.venv` 中（v1.41.1）。

### 3. 节点指标插入点：扩展 StatsCallbackHandler

**选择**：在 `StatsCallbackHandler.on_chain_end()` 和 `on_chain_error()` 中添加 Prometheus histogram/counter 记录，**不修改任何 `*_node.py` 文件**。

**替代方案**：给每个节点函数加装饰器——需要改动 8 个文件，且有签名兼容性风险。

**理由**：`StatsCallbackHandler` 已经通过 LangChain 回调捕获了每个节点的开始/结束/错误，有现成的 duration 数据。添加指标只需 3 行代码。

### 4. LLM Token 提取：Per-Provider 响应拦截

**选择**：在 `openai_llm.py` 的 `chat()`、`chat_with_tools()` 方法返回前提取 `response.usage`（prompt_tokens/completion_tokens），通过回调写入指标。GLM 已有 `_track_usage()`，直接对接。

**替代方案**：在 `TracingProxy._call_with_span()` 中统一拦截——但 `chat_stream` 是 async generator，最终 chunk 的 usage 信息在 generator 内部消费完才能拿到，TracingProxy 层拿不到。

**理由**：非流式调用在 provider 层提取最可靠。流式调用需在每个 provider 的 `chat_stream` 中特殊处理（OpenAI streaming 最后一帧含 usage）。

### 5. RAG 指标插入点：llm_node 现有计时位置

**选择**：`llm_node.py:189-198` 已有 `time.perf_counter()` 计时 RAG 检索，在其附近增加 OTel histogram 记录。`MemoryMiddleware.before_llm_call()` 返回的 `metadata` 中包含 `memory_count` 和 `fuzzy_count`，可直接作为 chunk count 指标。

**理由**：最小侵入——计时代码已存在，只需加一行 `histogram.record()` 和 `counter.add()`。

### 6. 基础设施：OTel Collector 兼作 Prometheus 指标端点

**选择**：OTel Collector 配置 `prometheus` exporter 在 `:8889` 暴露指标，Prometheus scrape 该端点。Tempo 接收 OTLP trace。Grafana 自动 provision Prometheus + Tempo 两个 datasource。

```
Anima Backend ──OTLP(grpc:4317)──▶ OTel Collector ──┬──▶ Tempo (traces)
                                     │                    │
                                     ├──▶ Prometheus :8889/metrics
                                     │        │
                                     └──▶ (future: logs)
                                          
Grafana :3000 ◀── datasources ── Prometheus :9090
                               ── Tempo :3200
```

## Risks / Trade-offs

- **[风险] OTLP gRPC 导出增加网络开销** → 缓解：使用 `BatchSpanProcessor` 批量发送，不影响请求关键路径。trace 丢失可接受（非业务数据）。
- **[风险] 流式 LLM 调用的 token 提取不可靠** → 缓解：对于 `chat_stream`，使用启发式估算（字符数 / 4 ≈ token 数）作为 fallback；非流式调用使用精确的 `response.usage`。
- **[风险] LLM pricing 表过期** → 缓解：在 `PROVIDER_PRICING` 字典中加 `# TODO: Update pricing as of YYYY-MM-DD` 注释。成本指标是 Counter 而非精确计费——有误差可接受。
- **[风险] docker-compose 增加本地资源消耗** → 缓解：4 个容器（Collector/Prometheus/Tempo/Grafana）总计约 500MB 内存，单机可承受。Config 中可选择性禁用。

## Open Questions

- Discord webhook URL 由用户自行配置在 `.env` 中，不 commit。默认情况下 Alertmanager 告警静默（webhook URL 为空时仅记录日志）。
- Grafana 默认账号 `admin/admin`，首次登录强制改密码——在 README 中注明。
