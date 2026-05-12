## MODIFIED Requirements

### Requirement: Spans written to StatsStore AND exported via OTLP
All completed spans SHALL be written to the StatsStore SQLite database via `StatsSpanExporter` AND exported to an OTel Collector via `OTLPSpanExporter` when the OTLP endpoint is configured.

#### Scenario: Dual export active
- **WHEN** `config/observability.yaml` has `otlp.enabled: true` and a valid `endpoint`
- **THEN** `BatchSpanProcessor(OTLPSpanExporter)` SHALL be added to the TracerProvider alongside the existing `SimpleSpanProcessor(StatsSpanExporter)`
- **THEN** each completed span SHALL be written to BOTH SQLite and the OTLP endpoint

#### Scenario: OTLP disabled
- **WHEN** `config/observability.yaml` has `otlp.enabled: false`
- **THEN** only `StatsSpanExporter` SHALL be active (single export to SQLite)
- **THEN** no gRPC connection to the Collector SHALL be attempted

#### Scenario: OTLP endpoint unreachable
- **WHEN** OTLP export is enabled but the Collector is not running
- **THEN** the system SHALL log a warning and continue (graceful degradation)
- **THEN** spans SHALL still be written to StatsStore SQLite

## ADDED Requirements

### Requirement: OTLP configuration in observability.yaml
The `config/observability.yaml` SHALL include an `otlp` section with `enabled`, `endpoint`, and `protocol` fields.

#### Scenario: OTLP config loaded
- **WHEN** the backend starts
- **THEN** the OTLP configuration SHALL be read from `config/observability.yaml` under the `otlp` key
- **THEN** the default endpoint SHALL be `http://localhost:4317` (gRPC)

### Requirement: OTel Collector, Prometheus, Tempo, Grafana via docker-compose
The observability stack SHALL be deployable with a single `docker-compose up -d` command.

#### Scenario: One-command startup
- **WHEN** user runs `docker-compose -f observability/docker-compose.yml up -d`
- **THEN** four containers SHALL start: otel-collector, prometheus, tempo, grafana
- **THEN** the OTel Collector SHALL listen on port 4317 (gRPC) and 4318 (HTTP) for OTLP data
- **THEN** Prometheus SHALL scrape the OTel Collector's `:8889/metrics` endpoint
- **THEN** Tempo SHALL receive traces via OTLP on port 4317
- **THEN** Grafana SHALL be accessible at `http://localhost:3000`

### Requirement: BatchSpanProcessor for OTLP export
The OTLP exporter SHALL use `BatchSpanProcessor` (not SimpleSpanProcessor) to avoid blocking the request path on network I/O.

#### Scenario: Batch export configuration
- **WHEN** OTLP export is enabled
- **THEN** spans SHALL be batched and exported in the background
- **THEN** the request path SHALL NOT be blocked by span export
