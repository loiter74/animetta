## Why

When the OTel Collector (port 4317) is not running, the backend continuously retries OTLP metric exports every 15 seconds via `PeriodicExportingMetricReader`. These retry logs flood the terminal and the background thread keeps running even after the user closes the application — because there is no graceful shutdown for the OTel `MeterProvider`. Disabling OTLP export by default stops the noise while preserving local StatsStore SQLite tracing.

## What Changes

- Set `otlp.enabled: false` in `config/observability.yaml` as the safe default
- OTLP export becomes opt-in: users enable it only when running the observability stack (`docker-compose -f observability/docker-compose.yml up -d`)
- **BREAKING**: Users who rely on OTLP export for Grafana dashboards will need to explicitly set `otlp.enabled: true` — but the observability stack is not running by default, so this is the correct behavior

## Capabilities

### New Capabilities
- `observability-config`: Observability configuration with safe defaults — OTLP export opt-in

### Modified Capabilities
- `otel-metrics`: OTLP metric export now disabled by default; requires explicit `otlp.enabled: true`
- `otel-tracing`: OTLP trace export now disabled by default; requires explicit `otlp.enabled: true`

## Impact

- **Config file**: `config/observability.yaml` — single line change: `enabled: true` → `enabled: false`
- **No code changes required**: `bootstrap.py` already checks `otlp_cfg.get("enabled", False)` — default `False` is the safe path
- **StatsStore SQLite**: Unaffected — continues to work regardless of OTLP setting
- **Grafana dashboards**: Will show no data until user enables OTLP and starts observability stack
