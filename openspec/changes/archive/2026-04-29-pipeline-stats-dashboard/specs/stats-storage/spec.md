## ADDED Requirements

### Requirement: SQLite database initialization
The system SHALL create a SQLite database at `data/stats.db` with two tables (`traces`, `spans`) and appropriate indexes on startup, creating the `data/` directory if it does not exist.

#### Scenario: Fresh start creates database and tables
- **WHEN** StatsStore initializes and `data/stats.db` does not exist
- **THEN** system creates the file and creates `traces` and `spans` tables with all required columns and indexes

#### Scenario: Existing database is reused
- **WHEN** StatsStore initializes and `data/stats.db` already exists
- **THEN** system connects to the existing database without recreating tables (using `IF NOT EXISTS`)

### Requirement: Traces table schema
The `traces` table SHALL store: `trace_id` (TEXT PK), `session_id`, `input_type`, `user_text`, `total_duration_ms` (REAL), `status`, `error_msg`, `created_at` (DATETIME). Index on `created_at DESC`.

#### Scenario: Trace record created with required fields
- **WHEN** `create_trace()` is called with trace_id, session_id, input_type, user_text
- **THEN** a row is inserted with those values, `status="running"`, and auto-generated `created_at`

### Requirement: Spans table schema with multi-Agent support
The `spans` table SHALL store: `span_id` (TEXT PK), `trace_id` (FK to traces), `parent_span_id` (TEXT, nullable), `node_name`, `duration_ms` (REAL), `status`, `input_summary`, `output_summary`, `created_at` (DATETIME). Indexes on `trace_id` and `node_name`.

#### Scenario: Span with null parent for single-agent
- **WHEN** `create_span()` is called without `parent_span_id`
- **THEN** `parent_span_id` column is stored as NULL

#### Scenario: Span with parent for multi-agent
- **WHEN** `create_span()` is called with a `parent_span_id` value
- **THEN** that value is stored, enabling hierarchical trace visualization in the future

### Requirement: Overview aggregation query
The system SHALL provide a method that returns: `total_requests`, `success_rate` (%), `avg_duration_ms`, and `p95_duration_ms`.

#### Scenario: Calculate P95 from successful traces
- **WHEN** `get_overview()` is called with 100 traces
- **THEN** P95 is calculated as the 95th percentile of `total_duration_ms` among successful traces

### Requirement: Node statistics aggregation
The system SHALL provide a method that returns per-node: `node_name`, `call_count`, `avg_duration_ms`, `min_duration_ms`, `max_duration_ms`, `error_count`, `error_rate` (%), ordered by `avg_duration_ms DESC`.

#### Scenario: Aggregate stats across all spans
- **WHEN** `get_node_stats()` is called
- **THEN** returns one row per distinct `node_name` with aggregated metrics

### Requirement: Recent traces with pagination
The system SHALL return recent traces ordered by `created_at DESC`, with `limit` (default 50) and `offset` parameters.

#### Scenario: Paginated trace listing
- **WHEN** `get_recent_traces(limit=20, offset=40)` is called
- **THEN** returns traces 41-60 ordered by newest first

### Requirement: Trace detail with spans
The system SHALL return a single trace's full metadata plus all associated spans ordered by `created_at ASC`.

#### Scenario: Retrieve complete trace
- **WHEN** `get_trace_detail(trace_id)` is called for an existing trace
- **THEN** returns trace metadata and array of spans with all fields

#### Scenario: Non-existent trace returns null
- **WHEN** `get_trace_detail()` is called with a non-existent trace_id
- **THEN** returns None
