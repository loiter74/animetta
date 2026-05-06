## Context

Anima 目前已有 StatsStore（SQLite 存储 traces/spans）和 StatsCallbackHandler（LangGraph 节点级自动计时），但 service 层（LLM.chat_stream、TTS.synthesize、ASR.transcribe 等）的方法调用完全没有耗时追踪。所有 Factory（LLMFactory / TTSFactory / ASRFactory / VADFactory）刚统一为 ProviderRegistry 模式，为统一注入 tracing 提供了入口。

## Goals / Non-Goals

**Goals:**
- 基于 OpenTelemetry 标准实现全链路追踪，覆盖 LangGraph 节点 → Service 方法 → 子步骤
- 在 Factory 层通过动态 Proxy 自动包装所有 service 实例，零修改业务代码
- 自定义 StatsSpanExporter 将 OTel Span 写入现有 StatsStore SQLite
- Dashboard 增强显示 span 树 / 火焰图

**Non-Goals:**
- 不做跨进程 trace 传播（不需要 W3C traceparent）
- 不做 Metrics / Logs（只做 Traces）
- 不替换现有的 StatsCallbackHandler（两者共存，Handler 负责节点级，OTel 请求级+方法级）

## Decisions

### D1: 用 OpenTelemetry API + SDK，不自己造

opentelemetry-api 提供了现成的 Tracer / Span / ContextVar 传播，opentelemetry-sdk 提供了 BatchSpanProcessor（后台线程批量写）。只需要实现一个 StatsSpanExporter（~30行），省去了自己写上下文管理、异步批量、采样逻辑的工作。

### D2: 动态 TracingProxy 通过 __getattr__ 实现

一个通用 Proxy 类拦截所有 async 方法调用，自动创建 span。不重复写 4 个接口 × 多个方法的代理代码。

```python
class TracingProxy:
    def __init__(self, target, tracer, service_name):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_tracer", tracer)
        object.__setattr__(self, "_service", service_name)

    async def __call_span(self, method_name, args, kwargs):
        span = self._tracer.start_span(f"{self._service}.{method_name}")
        try:
            result = await getattr(self._target, method_name)(*args, **kwargs)
            span.set_status(StatusCode.OK)
            return result
        except Exception as e:
            span.record_exception(e)
            span.set_status(StatusCode.ERROR, str(e))
            raise
        finally:
            span.end()

    def __getattr__(self, name):
        attr = getattr(self._target, name)
        if not name.startswith("_") and asyncio.iscoroutinefunction(attr):
            return lambda *a, **kw: self.__call_span(name, a, kw)
        return attr
```

### D3: TracingProxy 在 Factory.create() 里注入

修改 4 个 Factory 的 create() 方法，在返回前用 TracingProxy 包装。不修改 ProviderRegistry 核心逻辑。

```python
class LLMFactory:
    @staticmethod
    def create_from_config(config, system_prompt=""):
        llm = ProviderRegistry.create_service("llm", config, system_prompt=system_prompt)
        tracer = trace.get_tracer("anima")
        return TracingProxy(llm, tracer, "llm")
```

### D4: StatsSpanExporter 复写 StatsStore

```python
class StatsSpanExporter(SpanExporter):
    def export(self, spans):
        # 批量写入 StatsStore
        for span in spans:
            stats_store.create_span(
                span_id=span.context.span_id,
                trace_id=span.context.trace_id,
                parent_span_id=span.parent.span_id if span.parent else None,
                node_name=span.name,
                duration_ms=(span.end_time - span.start_time) / 1e6,
            )
        return Success
```

### D5: ContextVar 在 graph node 入口设置

在每个 graph node 函数入口，从 StatsCallbackHandler 获取当前 trace_id，通过 OTel 的 Context API attach 到当前上下文。这样 service 层 Proxy 创建的 span 自动成为子 span。

```python
def _attach_trace_context(state):
    handler = StatsCallbackHandler  # 当前 trace_id
    span_context = SpanContext(
        trace_id=handler._trace_id,
        span_id=generate_span_id(),
        is_remote=False,
    )
    ctx = trace.set_span_in_context(NonRecordingSpan(span_context))
    return context.attach(ctx)
```

### D6: StatsStore 扩展 OTel 标准字段

spans 表增加 attributes（JSON）、events（JSON）、status（TEXT）、kind（INTEGER）列。向后兼容，旧 span 行这些字段为 NULL。

### D7: Dashboard 增加火焰图组件

基于现有的 Chart.js 扩展，新增一个 Trace Detail 页，用嵌套条形图展示单个 trace 的 span 树。后端 API 增加 `/api/stats/traces/{id}/tree` 返回已按 parent_span_id 组装好的树结构。

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   应用启动时                                │
│                                                           │
│  provider = TracerProvider()                               │
│  provider.add_span_processor(BatchSpanProcessor(           │
│      StatsSpanExporter(stats_store)                        │
│  ))                                                        │
│  trace.set_tracer_provider(provider)                       │
│                                                           │
├─────────────────────────────────────────────────────────┤
│                   LangGraph 节点执行时                       │
│                                                           │
│  llm_node(state, config):                                  │
│    ctx = _attach_trace_context(state)  ← 从 Handler 拿 ID   │
│    await service.chat_stream(text)       ← Proxy 截获       │
│    context.detach(ctx)                                      │
│                                                           │
├─────────────────────────────────────────────────────────┤
│                   Service 方法调用时                         │
│                                                           │
│  TracingProxy:                                             │
│    __getattr__ → __call_span("chat_stream")                 │
│      → tracer.start_span("llm.chat_stream")                 │
│        → 自动从 ContextVar 继承 parent                       │
│        → 调用真实方法                                        │
│        → span.end()                                         │
│          → BatchSpanProcessor 队列 → StatsExporter 批量写    │
│                                                           │
├─────────────────────────────────────────────────────────┤
│                   StatsStore (SQLite)                      │
│                                                           │
│  traces 表: trace_id, session_id, ..., total_duration_ms    │
│  spans 表: span_id, trace_id, parent_span_id, node_name,   │
│            duration_ms, attributes, events, status, kind    │
│                                                           │
├─────────────────────────────────────────────────────────┤
│                   Dashboard                                 │
│                                                           │
│  /api/stats/traces/{id}/tree → 返回 span 树                 │
│  /stats/ → 增强，新增火焰图视图                               │
└─────────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| OTel 版本升级可能导致 API 不兼容 | 将 opentelemetry-api 版本固定在 requirements.txt |
| Proxy 动态 __getattr__ 性能开销 | 每个调用只触发一次 __getattr__ + 一次 span 创建，微秒级 |
| SQLite 写入压力（高频 span 写入） | BatchSpanProcessor 默认 5s 或 512 条一批，后台线程写 |
| OTel 与现有 StatsCallbackHandler trace_id 不一致 | 保持 StatsCallbackHandler.trace_id 作为唯一来源，OTel span context 对齐它 |
