## Context

Anima v2.0 基于 LangGraph 状态机，后端 FastAPI + Socket.IO。已有 OpenTelemetry 链路追踪骨架：`TracingProxy` 自动为 LLM/ASR/TTS/VAD 服务调用创建 OTel span，`StatsSpanExporter` 将 span 写入 SQLite StatsStore，`StatsCallbackHandler` 通过 LangChain 回调捕获节点耗时。`config/observability.yaml` 配置了 LangSmith + LangFuse + tracing 参数，但 **没有 OTLP 导出**、**没有任何 Prometheus 指标**、**LLM token 用量被丢弃**。

目标是把这套骨架扩展为端到端可观测性闭环，全本地化部署（单机 docker-compose），不引入 SaaS。

## Goals / Non-Goals

**Goals:**
- 一次对话的全链路 trace 能在 Grafana Tempo 中可视化（7 个 LangGraph 节点 span + 服务调用 span）
- 20+ 核心业务指标通过 OTel Metrics API 埋点，经 OTel Collector → Prometheus 可查询
- 4 张 Grafana dashboard 覆盖概览、Pipeline、RAG、成本
- 5 条关键告警通过 Discord / Email 通知
- Loki 日志聚合，接入 loguru 日志到 Grafana
- 一键启动：`docker-compose -f observability/docker-compose.yml up -d`

**Non-Goals:**
- 不引入 Datadog / Honeycomb / NewRelic 等 SaaS
- 不重写已有 OTel SDK 埋点（TracingProxy、StatsSpanExporter 保留）
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

### 6. 基础设施：OTel Collector 三路输出

**选择**：OTel Collector 配置 `prometheus` exporter 在 `:8889` 暴露指标，Prometheus scrape 该端点。Tempo 接收 OTLP trace + metrics。Loki 通过 Promtail 采集 loguru 日志文件。Grafana 自动 provision Prometheus + Tempo + Loki 三个 datasource。

```
Anima Backend ──OTLP(grpc:4317)──▶ OTel Collector ──┬──▶ Tempo (traces + metrics)
                                     │                    │
                                     ├──▶ Prometheus :8889/metrics
                                     │        │
                                     ├──▶ Loki (logs via filelog receiver)
                                     │        │
                                     │   logs/anima.log (host volume)
                                     │        │
                                     └──▶ Debug (stdout)
                                          
Grafana :3000 ◀── datasources ── Prometheus :9090
                                ── Tempo :3200
                                ── Loki :3100

Alertmanager ──webhook──▶ Notifier (Docker, :9094)
                            ├── Discord webhook
                            ├── 飞书 webhook
                            └── Email SMTP
```

## Decisions (cont.)

### 7. 通知架构：独立 Docker sidecar + 插件化 Notifier

**选择**：弃用 Alertmanager 的原生 Discord receiver，改用通用的 webhook receiver + 自定义 Notifier 服务。

```
Alertmanager ──webhook POST──▶ Notifier (:9094/api/v1/alerts)
                                   │
                                   ├── @register_notifier("discord")
                                   ├── @register_notifier("feishu")
                                   └── @register_notifier("email")
```

**理由**：
- Alertmanager 不支持飞书，也不方便自定义消息格式
- 插件架构（`NotifierBase` ABC + `@register_notifier`）复用 Anima 现有的 ProviderRegistry 模式
- Notifier 跑在 Docker 网络中，和 Alertmanager 同网络，不依赖宿主机后端是否可用

### 8. Notifier 部署方式：独立 Starlette 服务

**选择**：Notifier 是独立的 Python ASGI 应用（`src/anima/notifier/server.py` 中的 `create_notifier_app()`），通过 `Dockerfile.notifier` 打包，监听 `:9094`。

**替代方案**：和 stats_api 一样挂在 Anima 后端内——如果后端挂了告警通知也跟着挂。

**理由**：告警通知在故障场景最需要可用，独立部署避免与应用进程耦合。`python:3.13-slim` 镜像约 120MB，资源开销可忽略。

### 9. Loki 日志采集：OTel Collector filelog receiver

**选择**：使用 OTel Collector 内置的 `filelog` receiver 读取 `logs/anima.log`，通过 `loki` exporter 发送。不引入额外的 Alloy/Promtail 容器。

**替代方案**：Alloy 或 Promtail——功能相同但多一个容器。

**理由**：OTel Collector 已经部署了，`filelog` receiver 是 built-in 组件，零额外依赖。Anima 后端通过 `logger.add("logs/anima.log", rotation="10MB")` 输出文件日志。

### 10. 配置隔离：独立 `.env.notifier`

**选择**：Notifier 容器使用独立的 `.env.notifier` 文件，仅包含 `NOTIFIER_*` 和 `ALERT_*` 环境变量。

**替代方案**：复用根 `.env`——会导致 LLM API Key 等敏感信息暴露给 Notifier 容器。

**理由**：最小权限原则。`.env` 包含 `GLM_API_KEY`、`DEEPSEEK_API_KEY` 等敏感凭证，Notifier 不需要知道这些。

### 11. 前端端口冲突

**选择**：前端 Vite dev server 从 3000 改为 5173（`vite.config.ts`），Grafana 保持 `:3000`。

**理由**：`strictPort: true` 下端口冲突会直接报错。5173 是 Vite 默认端口，改动最小。

## Risks / Trade-offs

- **[风险] OTLP gRPC 导出增加网络开销** → 缓解：使用 `BatchSpanProcessor` 批量发送，不影响请求关键路径。trace 丢失可接受（非业务数据）。
- **[风险] 流式 LLM 调用的 token 提取不可靠** → 缓解：对于 `chat_stream`，使用启发式估算（字符数 / 4 ≈ token 数）作为 fallback；非流式调用使用精确的 `response.usage`。
- **[风险] LLM pricing 表过期** → 缓解：在 `PROVIDER_PRICING` 字典中加 `# TODO: Update pricing as of YYYY-MM-DD` 注释。成本指标是 Counter 而非精确计费——有误差可接受。
- **[风险] docker-compose 增加本地资源消耗** → 缓解：6 个容器（Collector/Prometheus/Tempo/Grafana/Alertmanager/Alloy 或 Promtail）总计约 700MB 内存，单机可承受。Config 中可选择性禁用。
- **[风险] Grafana 端口与前端冲突** → 缓解：前端 Vite dev server 从 3000 改为 5173（`vite.config.ts`），Grafana 保持 :3000。

## Open Questions

- Discord webhook URL 由用户自行配置在 `.env` 中，不 commit。默认情况下 Alertmanager 告警静默（webhook URL 为空时仅记录日志）。
- 邮件告警需要 SMTP 账户，用户自行在 `.env` 中配置 `ALERT_SMTP_*` 参数。
- Grafana 默认账号 `admin/admin`，首次登录强制改密码——在 README 中注明。
- Loki 日志采集使用 Grafana Alloy（轻量级 collector，替代 Promtail），支持从文件 tail 日志并自动解析 loguru 格式。
