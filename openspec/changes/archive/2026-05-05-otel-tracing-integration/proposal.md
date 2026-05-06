## Why

Anima 目前只有 LangGraph 层的节点级耗时统计（StatsCallbackHandler），service 级别的调用耗时（LLM.chat_stream、TTS.synthesize、ASR.transcribe、Memory 查询等）完全没有追踪。要排查性能瓶颈只能靠猜。

接入 OpenTelemetry 标准后，所有 service 调用自动产生 span，形成完整调用链树，数据写回 StatsStore SQLite，Dashboard 上能看到每个请求从 "用户输入 → LLM → TTS → 表情 → 输出" 每个子步骤的耗时分布。

## What Changes

- 添加 opentelemetry-api + opentelemetry-sdk 依赖
- 实现自定义 `StatsSpanExporter`，将 OTel Span 写入现有的 StatsStore SQLite
- 在应用启动时配置 `TracerProvider` + `BatchSpanProcessor(StatsSpanExporter())`
- 实现 `TracingProxy`，在 Factory 层（LLMFactory / TTSFactory / ASRFactory / VADFactory）自动包装所有 service 实例，每个方法调用自动创建 OTel Span
- 在 LangGraph node 入口设置 trace context，让 service 层的 span 自动挂到请求级 span 树下面
- 改造 StatsStore spans 表，增加 OTel 标准字段（attributes、events、status）
- 增强 Dashboard，增加 Span 树 / 火焰图视图

## Capabilities

### New Capabilities

- `otel-tracing`: 基于 OpenTelemetry 标准的全链路追踪，覆盖 LangGraph 节点 + Service 方法 + 子步骤

### Modified Capabilities

- `pipeline-stats`: StatsStore 数据模型扩展以支持 OTel 标准 span 字段，StatsAPI 新增 trace 详情接口

## Impact

- 新增依赖：`opentelemetry-api`、`opentelemetry-sdk`（轻量，无外部 exporter 依赖）
- 新增文件：核心 tracing 基础设施在 `src/anima/tracing/` 下
- 修改文件：
  - Factory 层（4 个工厂）返回 TracingProxy 包装实例
  - StatsStore 扩展表结构
  - StatsAPI 增加 span 树查询端点
  - Dashboard 前端增加火焰图组件
- 无破坏性变更，原有 StatsHandler 继续工作
- 通过开关控制是否启用 OTel tracing（默认启用）
