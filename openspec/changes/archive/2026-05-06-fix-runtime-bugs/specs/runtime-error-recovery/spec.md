## ADDED Requirements

### Requirement: Orchestrator degrades gracefully when service context is partially initialized
The LangGraph orchestrator SHALL handle `None` values for `service_context.config` without crashing. When config is unavailable, the orchestrator SHALL return empty defaults for persona and system prompt.

#### Scenario: process_text called with uninitialized service context
- **WHEN** `process_text` is called on an orchestrator whose `service_context.config` is `None`
- **THEN** the orchestrator SHALL NOT raise an AttributeError
- **THEN** the orchestrator SHALL return an empty persona dict and None system prompt
- **THEN** the orchestrator SHALL still process the user's text input

#### Scenario: Session creation awaits service context initialization
- **WHEN** a new session creates a ServiceContext with pooled engines
- **THEN** `load_cache()` SHALL be fully awaited before the context is used
- **THEN** `ctx.config` SHALL be set to the AppConfig object
- **THEN** `ctx.llm_engine` SHALL be set to the pooled LLM instance

### Requirement: ASR factory registers all available providers
The ASR factory SHALL make all provider implementations discoverable through the ProviderRegistry.

#### Scenario: faster_whisper ASR provider is available
- **WHEN** the server starts with `asr: faster_whisper` in config
- **THEN** the ProviderRegistry SHALL include `faster_whisper` in its registered ASR services
- **THEN** `ASRFactory.create("faster_whisper", ...)` SHALL return a `FasterWhisperASR` instance (not a `MockASR`)
- **THEN** The `from_config` method SHALL correctly read parameters from the Pydantic config object using attribute access

