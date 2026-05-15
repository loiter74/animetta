## ADDED Requirements

### Requirement: silero_vad.py is split by concern
The services/intelligence/vad/silero_vad.py file (454 lines) SHALL be split into detection logic and audio processing.

#### Scenario: Detection logic extracted
- **WHEN** silero_vad.py is refactored
- **THEN** core detection logic (model loading, get_speech_prob, detect_speech) SHALL be in a separate module
- **THEN** all existing tests SHALL still pass

#### Scenario: Audio processing extracted
- **WHEN** silero_vad.py is refactored
- **THEN** audio buffer management and callback orchestration SHALL be in a separate module

### Requirement: openai_llm.py is split by feature
The services/intelligence/llm/openai_llm.py file (430 lines) SHALL be split into streaming, tool calling, and history management modules.

#### Scenario: Streaming logic extracted
- **WHEN** openai_llm.py is refactored
- **THEN** the astream/chat stream generation logic SHALL be in a separate module

#### Scenario: Tool calling logic extracted
- **WHEN** openai_llm.py is refactored
- **THEN** tool call handling and response processing SHALL be in a separate module

#### Scenario: All existing imports resolve
- **WHEN** the refactored modules are imported
- **THEN** existing code that imports from openai_llm SHALL continue to work without changes
