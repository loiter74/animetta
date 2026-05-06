## ADDED Requirements

### Requirement: Kokoro TTS provider registration
The system SHALL register a new TTS provider type `kokoro` via `@ProviderRegistry.register("tts", "kokoro")` for config class and `@ProviderRegistry.register_service("tts", "kokoro")` for service class.

#### Scenario: Config class registration
- **WHEN** system loads TTS config with `type: kokoro`
- **THEN** the Pydantic discriminated union resolves to KokoroTTSConfig

#### Scenario: Service class registration
- **WHEN** `ProviderRegistry.create_service("tts", KokoroTTSConfig(...))` is called
- **THEN** it returns a `KokoroTTS` instance from `KokoroTTS.from_config(config)`

### Requirement: KokoroTTS implements TTSInterface
The `KokoroTTS` class SHALL implement `TTSInterface` with `async synthesize(text, output_path=None) -> Union[bytes, str]`.

#### Scenario: Synthesize returns audio bytes
- **WHEN** `synthesize("你好", output_path=None)` is called
- **THEN** it returns bytes of synthesized audio (WAV format)
- **AND** the audio duration is proportional to text length

#### Scenario: Synthesize writes to file
- **WHEN** `synthesize("你好", output_path="/tmp/out.wav")` is called
- **THEN** it writes audio data to the specified path and returns the path string

#### Scenario: Lazy model loading
- **WHEN** `KokoroTTS` is instantiated
- **THEN** the Kokoro model is NOT loaded until `synthesize()` is first called
- **AND** the model path is determined from config

### Requirement: KokoroTTSConfig validates parameters
The `KokoroTTSConfig` SHALL support configuration of voice, model path, device, and speed parameters.

#### Scenario: Config with Chinese female voice
- **WHEN** `KokoroTTSConfig(voice="zf_xiaobei")` is created
- **THEN** `voice` field is set to "zf_xiaobei"
- **AND** `type` field is `Literal["kokoro"]`

#### Scenario: Config with custom model path
- **WHEN** `KokoroTTSConfig(model_path="E:/anima_data/models/kokoro/kokoro-v1_1-zh.pth")` is created
- **THEN** synthesis uses the specified model file
- **AND** falls back to auto-download if file not found

### Requirement: Factory creates KokoroTTS from config
The `TTSFactory._build_config()` method SHALL support `provider == "kokoro"` to construct `KokoroTTSConfig`.

#### Scenario: Factory builds Kokoro config
- **WHEN** `TTSFactory.create("kokoro", voice="zf_xiaobei", model_path="...")` is called
- **THEN** it constructs `KokoroTTSConfig` with the provided kwargs
- **AND** calls `ProviderRegistry.create_service("tts", config)` to instantiate

### Requirement: services.yaml supports kokoro provider
The `config/services.yaml` SHALL include a `kokoro_glados` preset entry.

#### Scenario: Kokoro GLaDOS preset defined
- **WHEN** user sets `services.tts: kokoro_glados` in `config.yaml`
- **THEN** the `AppConfig` loads `kokoro_glados` from `services.yaml`
- **AND** resolves it to a `KokoroTTSConfig` with GLaDOS effects enabled
