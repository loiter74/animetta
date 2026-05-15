## MODIFIED Requirements

### Requirement: OTLP configuration in observability.yaml
The `config/observability.yaml` SHALL include an `otlp` section with `enabled`, `endpoint`, and `protocol` fields. The default value for `enabled` SHALL be `false` (opt-in).

#### Scenario: OTLP config loaded
- **WHEN** the backend starts
- **THEN** the OTLP configuration SHALL be read from `config/observability.yaml` under the `otlp` key
- **THEN** the default `enabled` value SHALL be `false` (OTLP export opt-in)
- **THEN** the default endpoint SHALL be `http://localhost:4317` (gRPC)
- **THEN** the config file SHALL include an inline comment explaining that `enabled: true` requires the observability stack to be running
