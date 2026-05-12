## 1. 基础设施搭建（A.1）

- [x] 1.1 创建 `observability/` 目录结构
- [x] 1.2 编写 `observability/docker-compose.yml`（OTel Collector + Prometheus + Tempo + Grafana）
- [x] 1.3 编写 `observability/otel-collector-config.yaml`（OTLP gRPC :4317 + Prometheus exporter :8889 + Tempo exporter）
- [x] 1.4 编写 `observability/prometheus.yml`（scrape OTel Collector :8889/metrics + alert rules 路径）
- [x] 1.5 编写 `observability/tempo-config.yaml`（OTLP receiver, local storage）
- [x] 1.6 编写 `observability/alertmanager.yml`（webhook 路由骨架）
- [x] 1.7 编写 `observability/grafana/provisioning/datasources/datasources.yml`（Prometheus + Tempo auto-provision）
- [x] 1.8 编写 `observability/grafana/provisioning/dashboards/dashboards.yml`（dashboard provider config）
- [x] 1.9 在 `config/observability.yaml` 新增 `otlp` 配置段（enabled, endpoint, protocol）
- [x] 1.10 修改 `src/anima/tracing/bootstrap.py`：`init_tracing()` 新增 OTLPSpanExporter（BatchSpanProcessor），双写模式
- [x] 1.11 在 `requirements.txt` / `pyproject.toml` 中声明 `opentelemetry-exporter-otlp-proto-grpc` 依赖
- [ ] 1.12 验收：`docker-compose up -d` → 启动 anima → 跑一次对话 → Grafana Explore → Tempo 能搜到完整 trace（含 7 个节点 span）

## 2. 业务指标埋点（A.2）

- [x] 2.1 创建 `src/anima/tracing/metrics.py`：初始化 OTel MeterProvider + 定义所有 Histogram/Counter/Gauge
- [x] 2.2 创建 `src/anima/tracing/cost_calculator.py`：PROVIDER_PRICING 字典 + `calculate_cost()` 函数
- [x] 2.3 在 `StatsCallbackHandler.on_chain_end()` 中记录 `anima_node_duration_seconds` histogram
- [x] 2.4 在 `StatsCallbackHandler.on_chain_error()` 中记录 `anima_node_errors_total` counter
- [x] 2.5 在 `openai_llm.py` 的 `chat()` / `chat_with_tools()` 中提取 `response.usage`，记录 token + cost 指标
- [x] 2.6 在 `openai_llm.py` 的 `chat_stream()` 中从最终 chunk 提取 usage 并记录指标
- [x] 2.7 在 `glm_llm.py` 中将 `_track_usage()` 对接到 metrics pipeline
- [x] 2.8 在 `llm_node.py` 的 RAG 检索计时处（L189-198）添加 `anima_rag_*` 指标
- [x] 2.9 在 `tool_node.py` 的工具循环（L47-86）中添加 `anima_tool_calls_total` + `anima_tool_duration_seconds`
- [x] 2.10 在 `routes.py` 的 `on_connect`/`on_disconnect` 中添加 `anima_active_sessions` Gauge
- [x] 2.11 在 `routes.py` 的消息处理中添加 `anima_session_messages_total` Counter
- [x] 2.12 在 `routes.py` 的错误处理中添加 `anima_websocket_errors_total` Counter
- [x] 2.13 在 `tts_node.py` / `asr_node.py` 中添加 ASR/TTS duration histogram（已有 TracingProxy 服务级埋点 + StatsCallbackHandler 节点级埋点覆盖）
- [ ] 2.14 验收：`curl http://localhost:9090/api/v1/label/__name__/values | grep anima_` 能列出所有 20+ 指标

## 3. Dashboard 设计（A.3）

- [x] 3.1 创建 `observability/grafana/dashboards/01-overview.json`（QPS, p50/p95/p99, 错误率, 成本率, 活跃会话）
- [x] 3.2 创建 `observability/grafana/dashboards/02-langgraph-pipeline.json`（节点延迟堆叠图, 错误率热图, 工具分布饼图）
- [x] 3.3 创建 `observability/grafana/dashboards/03-rag-performance.json`（检索延迟对比, 分块数分布, top score 直方图）
- [x] 3.4 创建 `observability/grafana/dashboards/04-cost-and-tokens.json`（累计成本曲线, token 趋势, 提供商占比, 月度预测）
- [x] 3.5 所有 dashboard 加 `session_id` 变量用于下钻
- [ ] 3.6 验收：进 Grafana，4 个 dashboard 都能打开且有数据；截图保存到 `docs/screenshots/`

## 4. 告警（A.4）

- [x] 4.1 编写 `observability/alerts/rules.yml`（5 条 Prometheus alert rules）
- [x] 4.2 完善 `observability/alertmanager.yml`（Discord webhook 路由 + Slack 备选）
- [x] 4.3 在 `.env.example` 中添加 `ALERT_WEBHOOK_URL` 占位说明
- [ ] 4.4 验收：手动断 LLM API key → 跑对话触发错误 → 5 分钟内收到 Discord 告警 → 恢复后收到 resolved

## 5. README 更新（A.5）

- [x] 5.1 在 `README.md` 新增 `## Observability` 章节
- [x] 5.2 包含：可观测性栈介绍, `docker-compose up -d` 启动命令, 端口表 (Grafana:3000, Prometheus:9090, Tempo:3200), 默认账号密码, 4 张 dashboard 截图
