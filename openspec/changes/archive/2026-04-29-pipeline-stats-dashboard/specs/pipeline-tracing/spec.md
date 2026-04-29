## ADDED Requirements

### Requirement: Trace lifecycle management
The system SHALL create a Trace record when a LangGraph graph execution begins (before `graph.ainvoke()`), and update it with total duration and final status when execution completes or fails.

#### Scenario: Successful text request creates completed trace
- **WHEN** user sends text input and LangGraph completes successfully
- **THEN** system creates a trace with `input_type="text"`, `user_text` (truncated to 100 chars), `status="success"`, and `total_duration_ms` measured from start to end

#### Scenario: Failed request creates error trace
- **WHEN** LangGraph execution raises an exception
- **THEN** system creates a trace with `status="error"` and `error_msg` containing the exception message (truncated to 500 chars)

### Requirement: Span collection via Callback Handler
The system SHALL implement a `StatsCallbackHandler` extending `langchain_core.callbacks.BaseCallbackHandler` that records each known node's execution as a Span linked to the current Trace.

#### Scenario: Node execution creates span with timing
- **WHEN** a known node (asr, llm, tts, emotion, output, tools) starts and completes
- **THEN** system creates a span with `node_name`, `duration_ms` (wall-clock), `status="success"`, and `input_summary` / `output_summary` (truncated to 200 chars each)

#### Scenario: Unknown nodes are ignored
- **WHEN** an internal LangGraph node (e.g., `_RouteInput`, `_ShouldUseTools`) triggers on_chain_start
- **THEN** system skips recording a span for that node

#### Scenario: Node error records error span
- **WHEN** a known node execution triggers on_chain_error
- **THEN** system records a span with `status="error"` and `output_summary` containing the error message

### Requirement: Callback injection without modifying node code
The system SHALL inject `StatsCallbackHandler` into LangGraph's callback list at the orchestrator level only. No existing node files (asr_node.py, llm_node.py, tts_node.py, emotion_node.py, output_node.py, tool_node.py) SHALL be modified.

#### Scenario: Handler added to LangGraph config
- **WHEN** orchestrator initializes `_run_graph()`
- **THEN** `StatsCallbackHandler` is appended to `run_config["callbacks"]` alongside existing observability callbacks

### Requirement: Non-blocking callback writes
The system SHALL write trace/span data asynchronously using `asyncio.ensure_future()` so that callback execution does not block the main LangGraph pipeline.

#### Scenario: SQLite write failure does not affect pipeline
- **WHEN** a callback write to SQLite raises an exception
- **THEN** system logs a warning and continues; the LangGraph pipeline is not interrupted
