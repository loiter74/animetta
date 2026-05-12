## Why

Anima 已有 OpenTelemetry 链路追踪骨架（TracingProxy、StatsSpanExporter → SQLite），但 trace 数据困在本地 SQLite 里，缺乏端到端可视化、业务指标、成本追踪和告警。一次对话经过 7 个 LangGraph 节点 + LLM/ASR/TTS 多次服务调用，运维完全黑盒——不知道 p95 延迟、不知道花了多少钱、不知道 RAG 召回质量。现在是时候把骨架变成真正能用的可观测性闭环。

## What Changes

- **OTel Collector + Prometheus + Tempo + Grafana 全本地化部署**：docker-compose 一键启动，不引入 SaaS
- **OTLP 双写导出**：保持现有 StatsSpanExporter (SQLite) 的同时，新增 OTLPSpanExporter 将 trace 发送到 OTel Collector → Tempo
- **业务指标埋点**：使用 OpenTelemetry Metrics API 埋 20+ 个核心指标（节点延迟、LLM token/cost、RAG 召回、WebSocket 会话等）
- **LLM 成本计算器**：覆盖 DeepSeek/GLM/OpenAI 的 pricing 表，从 API 响应中提取 token 用量自动计算 cost
- **4 张 Grafana Dashboard**：Overview / LangGraph Pipeline / RAG Performance / Cost & Tokens
- **5 条 Prometheus 告警**：高错误率、高延迟、成本预警/严重、服务宕机，路由到 Discord/Slack webhook
- **README 更新**：可观测性栈 setup 指引 + 截图

## Capabilities

### New Capabilities
- `otel-metrics`: OpenTelemetry Metrics API 埋点，通过 OTel Collector 暴露 Prometheus 端点，覆盖 LangGraph 节点、LLM、RAG、ASR/TTS、WebSocket、Tool 六层指标
- `grafana-dashboards`: 4 张预置 Grafana dashboard（Overview、LangGraph Pipeline、RAG Performance、Cost & Tokens），通过 provisioning 自动加载，支持 session_id 下钻
- `llm-cost-tracking`: 成本计算器 + Token 用量追踪，覆盖 DeepSeek/GLM/OpenAI/EdgeTTS/GPT-SoVITS，从 LLM API response.usage 自动提取
- `alerting-rules`: Prometheus Alertmanager 告警规则 + webhook 路由，5 条关键告警（错误率、延迟、成本、宕机）

### Modified Capabilities
- `otel-tracing`: 新增 OTLP gRPC 导出能力——在现有 StatsSpanExporter (SQLite) 基础上并行添加 OTLPSpanExporter，实现 trace 数据双写。config/observability.yaml 新增 otlp 配置段。**非 BREAKING**——现有 StatsStore + stats API 保持不变。

## Impact

- **新增目录**: `observability/`（docker-compose、Collector/Prometheus/Tempo/Alertmanager 配置、Grafana dashboard JSON）
- **新增文件**: `src/anima/tracing/metrics.py`、`src/anima/tracing/cost_calculator.py`、`observability/alerts/rules.yml`
- **修改文件**: `config/observability.yaml`（+otlp 段）、`src/anima/tracing/bootstrap.py`（+OTLPSpanExporter）、`src/anima/tracing/proxy.py`（+metrics 埋点）、`src/anima/services/intelligence/llm/openai_llm.py`（+token 提取）、`src/anima/orchestration/graph/stats_handler.py`（+Prometheus 指标）、`src/anima/orchestration/graph/tool_node.py`（+工具指标）、`src/anima/orchestration/graph/llm_node.py`（+RAG 指标）、`src/anima/orchestration/server/routes.py`（+会话指标）、`src/anima/orchestration/server/session.py`（+Gauge）
- **新增依赖**: `opentelemetry-exporter-otlp-proto-grpc`（已在 .venv 中）、`prometheus-client`（OTel Collector 端）
- **不影响**: 现有 LangGraph 节点签名、服务接口、stats API、前端
