## ADDED Requirements

### Requirement: LLM provider interface contract
All LLM provider implementations SHALL implement LLMInterface and be creatable via from_config.

#### Scenario: MockLLM creates with from_config
- **WHEN** MockLLM.from_config() is called
- **THEN** it SHALL return a MockLLM instance

#### Scenario: OpenAILLM creates with from_config
- **WHEN** OpenAILLM.from_config() is called with valid config
- **THEN** it SHALL return an OpenAILLM instance

#### Scenario: GLMLLM creates with from_config
- **WHEN** GLMLLM.from_config() is called
- **THEN** it SHALL return a GLMLLM instance

#### Scenario: OllamaLLM creates with from_config
- **WHEN** OllamaLLM.from_config() is called
- **THEN** it SHALL return an OllamaLLM instance

#### Scenario: LLMFactory.create falls back to Mock
- **WHEN** LLMFactory.create is called with an unknown provider
- **THEN** it SHALL return a MockLLM instance

#### Scenario: LLMFactory.create_from_config creates from config object
- **WHEN** LLMFactory.create_from_config is called with a valid LLMConfig
- **THEN** it SHALL return the appropriately typed LLM service

#### Scenario: LangChain adapter wraps LLMInterface
- **WHEN** LLMChatModelAdapter is created with an LLM service
- **THEN** it SHALL produce a valid BaseChatModel

### Requirement: ASR provider interface contract
All ASR provider implementations SHALL implement ASRInterface.

#### Scenario: MockASR transcribe returns test text
- **WHEN** MockASR.transcribe() is called with audio data
- **THEN** it SHALL return a transcription string

#### Scenario: ASRFactory.create falls back to Mock
- **WHEN** ASRFactory.create is called with unknown provider
- **THEN** it SHALL return a MockASR instance

### Requirement: TTS provider interface contract
All TTS provider implementations SHALL implement TTSInterface.

#### Scenario: MockTTS synthesize returns mock audio
- **WHEN** MockTTS.synthesize() is called with text
- **THEN** it SHALL return mock audio bytes

#### Scenario: TTSFactory.create falls back to Mock
- **WHEN** TTSFactory.create is called with unknown provider
- **THEN** it SHALL return a MockTTS instance

### Requirement: VAD provider interface contract
All VAD provider implementations SHALL implement VADInterface.

#### Scenario: MockVAD detect returns non-speech
- **WHEN** MockVAD.detect_speech() is called
- **THEN** it SHALL return a VADResult

#### Scenario: VADFactory.create_from_config creates from config
- **WHEN** VADFactory.create_from_config is called with valid config
- **THEN** it SHALL return a VADInterface instance

### Requirement: GLM message converter
GLMMessageConverter and GLMToolConverter SHALL correctly convert message formats.

#### Scenario: GLMMessageConverter converts LangChain messages to GLM format
- **WHEN** convert_messages() is called with BaseMessage list
- **THEN** it SHALL return GLM-format message dicts

#### Scenario: GLMToolConverter converts tool schemas
- **WHEN** convert_tools() is called with LangChain tool definitions
- **THEN** it SHALL return GLM-format tool definitions
