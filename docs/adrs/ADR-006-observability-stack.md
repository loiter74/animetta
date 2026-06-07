# ADR-006: Observability Stack

**Date:** 2026-06-07
**Status:** Accepted

## Context

Anima needs comprehensive observability for debugging, performance monitoring, and operational insights. The system has multiple async components (ASR, LLM, TTS, Live2D) that need tracing, metrics, and logging.

## Decision

Implement a full observability stack using OpenTelemetry (OTel) as the telemetry SDK:

1. **Tracing**: OTel SDK with custom `StatsSpanExporter` that stores spans in `StatsStore` for dashboard display
2. **Metrics**: Prometheus-compatible metrics endpoint at `/metrics`
3. **Logging**: Structured logging with loguru, correlated with traces via trace IDs
4. **Dashboard**: Grafana dashboards for real-time monitoring

### Architecture

```
┌─────────────────┐
│   Anima App     │
│  ┌───────────┐  │
│  │ OTel SDK  │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │StatsStore │  │
│  └───────────┘  │
└────────┬────────┘
         │
    ┌────▼────┐
    │ OTel    │
    │Collector│
    └────┬────┘
         │
  ┌──────┼──────┐
  │      │      │
  ▼      ▼      ▼
Prometheus Tempo Loki
```

### Key Design Decisions

1. **StatsSpanExporter**: Custom exporter that extracts key metrics (latency, token counts, errors) from spans and stores them in `StatsStore` for the frontend dashboard. This avoids requiring a full OTel collector for basic metrics.

2. **Idempotent initialization**: `init_tracing()` uses a module-level guard (`_TRACER_INITIALIZED`) to prevent duplicate initialization when called multiple times.

3. **Graceful degradation**: If OTel exporters fail, the system falls back to `_NoOpStatsStore` and continues without observability.

## Consequences

- **Positive**: Full trace visibility across async operations, Prometheus-compatible metrics, dashboard-ready data
- **Positive**: Idempotent init prevents "Overriding of current TracerProvider" warnings
- **Negative**: Additional complexity in service initialization
- **Negative**: StatsStore storage grows over time (mitigated by TTL cleanup)
