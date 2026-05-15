## Context

The Anima backend initializes OpenTelemetry tracing and metrics in `src/anima/tracing/bootstrap.py`. When `config/observability.yaml` has `otlp.enabled: true`, the `init_tracing()` function creates:

1. `OTLPSpanExporter` + `BatchSpanProcessor` — for trace export to `localhost:4317`
2. `OTLPMetricExporter` + `PeriodicExportingMetricReader` (15s interval) — for metric export

The `PeriodicExportingMetricReader` runs a background thread that retries on failure. When the OTel Collector is not running (the default state — user must manually start `observability/docker-compose.yml`), each retry logs a `StatusCode.UNAVAILABLE` error. The Python process has no `atexit` shutdown for the OTel `MeterProvider`, so the thread can outlive the application.

The code in `bootstrap.py:94` already guards OTLP initialization behind `otlp_cfg.get("enabled", False)` — the default of `False` means OTLP is off. The issue is purely the config file default.

## Goals / Non-Goals

**Goals:**
- Eliminate OTLP export retry noise when observability stack is not running
- Keep local StatsStore SQLite tracing fully functional
- Make OTLP export explicitly opt-in

**Non-Goals:**
- Adding graceful shutdown for OTel providers (future work, tracked separately)
- Changing the observability stack itself
- Modifying Grafana dashboards or Prometheus config

## Decisions

**Decision: Change config default, not code behavior**

The `bootstrap.py` code already has correct guard logic: `otlp_cfg.get("enabled", False)`. The `False` default means "OTLP is off unless explicitly enabled." No code change needed.

**Alternative considered: Add `atexit` shutdown hook**

Adding `atexit.register(shutdown_tracing)` in `bootstrap.py` would gracefully close the `PeriodicExportingMetricReader` background thread. Rejected for this change because:
- It doesn't fix the root issue (unnecessary connection attempts when Collector isn't running)
- It's a separate concern that should be tracked as its own improvement
- Config change is zero-risk and immediately effective

## Risks / Trade-offs

- **[Risk]**: Users who previously had OTLP data flowing to Grafana will see no new data after this change
  → **Mitigation**: Document the opt-in step in the config file comment. Users running the observability stack are already managing `docker-compose`, so toggling one line is trivial
- **[Risk]**: If someone deploys Anima with the observability stack and forgets to re-enable, metrics will silently stop
  → **Mitigation**: The config file includes a comment explaining when to enable. A future improvement could add a startup warning when `prometheus:9090` is reachable but OTLP export is disabled
