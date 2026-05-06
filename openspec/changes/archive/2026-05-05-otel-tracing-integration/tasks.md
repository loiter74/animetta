## 1. Dependencies & Config

- [x] 1.1 Add `opentelemetry-api` and `opentelemetry-sdk` to requirements.txt
- [x] 1.2 Create `src/anima/tracing/` package with `__init__.py`
- [x] 1.3 Add tracing enable/disable config to `config/observability.yaml`

## 2. StatsSpanExporter

- [x] 2.1 Implement `StatsSpanExporter(SpanExporter)` with `export()` method writing to StatsStore
- [x] 2.2 Implement `shutdown()` and `force_flush()` on the exporter
- [x] 2.3 Handle `Span` → `stats_store.create_span()` mapping (trace_id, span_id, parent_span_id, name, duration, attributes, status)
- [x] 2.4 Handle `Span` events and exception recording in attributes
- [x] 3.1 Create `init_tracing()` function: configure `TracerProvider` + `BatchSpanProcessor(StatsSpanExporter)`
- [x] 3.2 Integrate `init_tracing()` into server startup (`websocket.py::create_server`)
- [x] 6.1 Extract current trace_id from StatsCallbackHandler at graph node entry → in orchestrator._run_graph()
- [x] 6.2 Create `attach_trace_context()` + `detach_trace_context()` helpers
- [x] 6.3 Attach OTel context in `orchestrator._run_graph()` (single injection point)
- [x] 6.4 OTel span tree inherits StatsHandler trace_id via context propagation

## 7. StatsStore Schema Extension

- [x] 7.1 Add `attributes TEXT`, `events TEXT`, `kind INTEGER` columns to spans table
- [x] 7.2 Existing `create_span()/finish_span()` continue working; OTel fields added via migration
- [x] 7.3 Update `StatsStore.get_trace_detail()` to return new fields
- [x] 8.1 Add `GET /api/stats/traces/{trace_id}/tree` endpoint
- [x] 8.2 Implement `_build_span_tree()` tree builder

## 9. Dashboard Enhancement

- [x] 9.1 Add flame chart / span tree visualization to frontend/stats/stats.js
- [x] 9.2 Wire trace detail modal to use /api/stats/traces/{id}/tree endpoint
- [x] 9.3 Display span tree with horizontal bars + flame chart CSS

## 10. Testing

- [x] 10.1 Unit tests for StatsSpanExporter (7 tests)
- [x] 10.2 Unit tests for TracingProxy (10 tests: async, sync, exception, lazy, property, generator, repr, len)
- [~] 10.3 Integration test: full flow (requires running app to verify end-to-end)
- [x] 10.4 NoOp mode — built into bootstrap.py (NoOpTracerProvider when disabled)
