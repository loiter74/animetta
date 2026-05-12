## ADDED Requirements

### Requirement: ServicePool lifecycle tests
ServicePool SHALL be tested for init, get_context, and shutdown lifecycle with mocked ServiceContext.

#### Scenario: ServicePool init creates shared engines
- **WHEN** ServicePool.init() is called with a valid config
- **THEN** it SHALL initialize ServiceContext and extract LLM/TTS/ASR engines as class-level singletons

#### Scenario: ServicePool.get_context returns dict
- **WHEN** ServicePool.get_context() is called after init
- **THEN** it SHALL return a dict with llm_engine, tts_engine, asr_engine keys

#### Scenario: ServicePool shutdown closes engines
- **WHEN** ServicePool.shutdown() is called
- **THEN** it SHALL close all shared engine instances

#### Scenario: ServicePool.is_ready reflects state
- **WHEN** ServicePool is initialized
- **THEN** is_ready() SHALL return True

### Requirement: socketio_server entry point
The socketio_server module SHALL be tested for its factory functions and configuration loading.

#### Scenario: get_asgi_app creates server
- **WHEN** get_asgi_app() is called with a mock config
- **THEN** it SHALL return a Starlette ASGI app

#### Scenario: parse_server_args handles flags
- **WHEN** parse_server_args is called with --redis-url flag
- **THEN** it SHALL parse the redis URL correctly

### Requirement: ServiceContext factory methods
ServiceContext SHALL have tested factory methods for each service type.

#### Scenario: load_from_config sequences initialization
- **WHEN** load_from_config is called
- **THEN** it SHALL call init_asr, init_tts, init_llm, init_vad, init_memory, init_emotion_analyzer in order

#### Scenario: load_cache reuses shared engines
- **WHEN** load_cache is called with shared engine instances
- **THEN** it SHALL use those instances instead of creating new ones

#### Scenario: close cleans up all services
- **WHEN** close() is called
- **THEN** it SHALL call close on all initialized services

### Requirement: ModelLoadingManager warmup
ModelLoadingManager SHALL handle concurrent model loading and state tracking.

#### Scenario: warmup loads all registered models
- **WHEN** warmup() is called
- **THEN** it SHALL load all registered models concurrently

#### Scenario: get triggers lazy loading
- **WHEN** get() is called for an unloaded model
- **THEN** it SHALL trigger lazy loading with timeout

#### Scenario: get_status returns state snapshot
- **WHEN** get_status() is called
- **THEN** it SHALL return a dict of model states
