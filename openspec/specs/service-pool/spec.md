### Requirement: LLM/TTS/ASR engines are globally shared
The system SHALL maintain a single shared instance of LLM, TTS, and ASR engines that all sessions reuse.

#### Scenario: Multiple sessions share engines
- **WHEN** two or more sessions are created
- **THEN** they SHALL use the same LLM engine, TTS engine, and ASR engine instances

#### Scenario: Each session has own VAD and Memory
- **WHEN** a session is created
- **THEN** it SHALL have its own VAD engine instance and Memory system instance

### Requirement: Session context creation is fast
When ServicePool is ready, creating a new session context SHALL NOT reinitialize shared engines.

#### Scenario: Fast session creation
- **WHEN** ServicePool is ready and a new session context is created
- **THEN** the creation SHALL skip LLM/TTS/ASR initialization and only create VAD + Memory

### Requirement: Graceful degradation
When ServicePool is not available, the system SHALL fall back to full per-session initialization.

#### Scenario: No pool fallback
- **WHEN** ServicePool is not ready
- **THEN** session creation SHALL use the existing load_from_config() code path
