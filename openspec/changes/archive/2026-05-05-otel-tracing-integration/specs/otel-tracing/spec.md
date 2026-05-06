## ADDED Requirements

### Requirement: Service calls produce OTel spans
Every service method call (LLM.chat_stream, TTS.synthesize, ASR.transcribe, VAD.detect_speech) SHALL automatically produce an OpenTelemetry span.

#### Scenario: LLM chat_stream traced
- **WHEN** llm_node calls service.chat_stream("你好")
- **THEN** a span named "llm.chat_stream" SHALL be created with start_time, end_time, and duration

#### Scenario: TTS synthesize traced
- **WHEN** tts_node calls service.synthesize("你好")
- **THEN** a span named "tts.synthesize" SHALL be created

#### Scenario: Service error captured
- **WHEN** a service method raises an exception
- **THEN** the span SHALL have status=ERROR and record the exception

### Requirement: Span hierarchy matches call tree
Spans SHALL form a parent-child tree matching the actual call hierarchy: LangGraph node → service method → sub-operations.

#### Scenario: Nested span creation
- **WHEN** llm_node calls chat_stream which internally calls an HTTP API
- **THEN** the "llm.chat_stream" span SHALL have as parent the "llm_node" span
- **THEN** each sub-operation SHALL be a child span of "llm.chat_stream"

#### Scenario: Context propagation across async boundaries
- **WHEN** a service method is called from an async context
- **THEN** the span SHALL correctly inherit the parent trace context via ContextVar

### Requirement: Spans written to StatsStore
All completed spans SHALL be written to the StatsStore SQLite database via a custom SpanExporter.

#### Scenario: Export to StatsStore
- **WHEN** a span ends
- **THEN** BatchSpanProcessor SHALL eventually call StatsSpanExporter.export()
- **THEN** a row SHALL exist in the spans table with trace_id, span_id, parent_span_id, name, duration_ms

#### Scenario: Batch writing
- **WHEN** many spans end in quick succession
- **THEN** they SHALL be batched and written at once (max 512 spans or 5s interval)

### Requirement: Dashboard shows span tree
The existing stats dashboard SHALL display individual trace detail as a span tree / flame chart.

#### Scenario: View trace tree
- **WHEN** user clicks a trace in the trace list
- **THEN** the detail view SHALL show all spans organized by parent_span_id as a nested tree
- **THEN** each span SHALL display name, duration_ms, and status

### Requirement: Tracing can be disabled
The tracing infrastructure SHALL support being disabled via configuration without code changes.

#### Scenario: Disable tracing
- **WHEN** tracing is disabled in config
- **THEN** NoOpTracerProvider SHALL be used (zero overhead)
- **THEN** no spans SHALL be created or written
