## MODIFIED Requirements

### Requirement: OTel MeterProvider initialized
The system SHALL initialize an OpenTelemetry MeterProvider alongside the existing TracerProvider during `init_tracing()`. Metrics SHALL be exported to the OTel Collector via OTLP only when `otlp.enabled` is explicitly set to `true` in `config/observability.yaml`.

#### Scenario: MeterProvider created at startup (OTLP disabled — default)
- **WHEN** the backend starts and `init_tracing()` is called with `otlp.enabled: false` (the default)
- **THEN** a MeterProvider SHALL be created with the same `service.name` resource attribute as the TracerProvider
- **THEN** NO PeriodicExportingMetricReader SHALL be configured (no OTLP gRPC connection attempted)
- **THEN** metric instruments SHALL still be defined and usable for local consumption (e.g., via `http://localhost:8889` when Collector is running)

#### Scenario: MeterProvider created at startup (OTLP enabled — opt-in)
- **WHEN** the backend starts and `init_tracing()` is called with `otlp.enabled: true`
- **THEN** a PeriodicExportingMetricReader SHALL be configured with an OTLP gRPC metric exporter pointing to the configured endpoint (default: `http://localhost:4317`)

#### Scenario: Metrics disabled when tracing disabled
- **WHEN** `config/observability.yaml` has `tracing.enabled: false`
- **THEN** no MeterProvider SHALL be created (no metrics overhead)
