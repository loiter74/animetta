## ADDED Requirements

### Requirement: Settings panel displays real-time backend config
The frontend SHALL request and display the current backend configuration (active services, persona, model paths) instead of hardcoded defaults.

#### Scenario: Load config on settings open
- **WHEN** user opens the settings panel
- **THEN** the frontend SHALL emit `get_config` socket event
- **AND** display the received `config_data` in the UI

#### Scenario: Display active services
- **WHEN** config data is received
- **THEN** the ASR/TTS/LLM/VAD service names SHALL be displayed with their actual active provider names

#### Scenario: Display persona info
- **WHEN** config data is received
- **THEN** the persona name SHALL be shown

#### Scenario: Display Live2D model info
- **WHEN** config data is received
- **THEN** the Live2D model path SHALL be displayed

### Requirement: Backend exposes config via socket event
The backend SHALL handle `get_config` socket event and respond with `config_data` containing safe (no API keys) configuration data.

#### Scenario: Backend returns config
- **WHEN** server receives `get_config` event
- **THEN** it SHALL respond with `config_data` containing persona, services, active_services, live2d, and system fields
- **AND** SHALL NOT include any API keys or secrets
