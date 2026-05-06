## MODIFIED Requirements

### Requirement: Spans table supports OTel fields
The spans table in StatsStore SHALL support additional fields required by OpenTelemetry: attributes, events, status, kind.

#### Scenario: OTel span stored with all fields
- **WHEN** an OTel span is exported to StatsStore
- **THEN** the spans table SHALL store attributes (JSON), events (JSON), status (TEXT), kind (INTEGER) alongside existing fields
- **THEN** existing non-OTel spans SHALL continue to work with these fields as NULL

### Requirement: Trace detail API returns span tree
The StatsAPI SHALL provide an endpoint that returns spans organized as a tree (grouped by parent_span_id).

#### Scenario: Tree endpoint returns structured spans
- **WHEN** GET /api/stats/traces/{trace_id}/tree
- **THEN** response SHALL contain a nested tree structure: {span, children: [...]}
- **THEN** root spans SHALL have parent_span_id = NULL
