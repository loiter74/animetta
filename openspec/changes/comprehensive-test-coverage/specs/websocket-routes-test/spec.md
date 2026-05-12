## ADDED Requirements

### Requirement: Socket.IO event routing
RouteHandlers SHALL correctly dispatch socket events to appropriate handlers.

#### Scenario: on_text_input processes text
- **WHEN** text_input event is received with text data
- **THEN** it SHALL call orchestrator.process_text()

#### Scenario: on_raw_audio_data feeds VAD processor
- **WHEN** raw_audio_data event is received
- **THEN** it SHALL feed audio chunk to the VAD processor

#### Scenario: on_mic_audio_end triggers ASR pipeline
- **WHEN** mic_audio_end event is received
- **THEN** it SHALL call processor.process_end()

#### Scenario: on_interrupt_signal aborts generation
- **WHEN** interrupt_signal event is received
- **THEN** it SHALL call InterruptHandler.set_interrupt()

#### Scenario: on_connect handles new connection
- **WHEN** connect event fires
- **THEN** it SHALL register the session

#### Scenario: on_disconnect cleans up session
- **WHEN** disconnect event fires
- **THEN** it SHALL clean up session resources

### Requirement: Session management
SessionManager SHALL manage orchestrator lifecycle per client session.

#### Scenario: get_or_create_context reuses pool engines
- **WHEN** get_or_create_context() is called
- **THEN** it SHALL check ServicePool for shared engines first

#### Scenario: get_or_create_orchestrator creates from config
- **WHEN** get_or_create_orchestrator() is called
- **THEN** it SHALL load tools config and create LangGraphOrchestrator

#### Scenario: cleanup_session removes all resources
- **WHEN** cleanup_session() is called
- **THEN** it SHALL stop orchestrator, reset audio processor, close context

### Requirement: Server lifecycle
LifecycleManager SHALL handle graceful shutdown.

#### Scenario: signal handlers set shutdown event
- **WHEN** SIGINT signal is received
- **THEN** shutdown_event SHALL be set

#### Scenario: cleanup_all runs registered callbacks
- **WHEN** cleanup_all() is called
- **THEN** all registered cleanup callbacks SHALL execute

### Requirement: Stats API endpoints
Stats API SHALL serve correct health and metrics data.

#### Scenario: health endpoint returns ok
- **WHEN** GET /health is called
- **THEN** it SHALL return {"status": "ok"}

#### Scenario: stats overview returns data
- **WHEN** GET /api/stats/overview is called
- **THEN** it SHALL return overview statistics from StatsStore

#### Scenario: stats nodes returns per-node data
- **WHEN** GET /api/stats/nodes is called
- **THEN** it SHALL return per-node latency statistics
