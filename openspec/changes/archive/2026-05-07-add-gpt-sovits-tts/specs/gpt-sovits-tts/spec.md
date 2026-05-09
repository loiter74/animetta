## ADDED Requirements

### Requirement: GPT-SoVITS TTS provider

The system SHALL provide a `gpt_sovits` TTS provider that connects to a running GPT-SoVITS v2 API server (`api_v2.py`) via HTTP REST API to perform voice cloning text-to-speech synthesis.

#### Scenario: Synthesize speech with default reference audio

- **WHEN** the user configures `tts: gpt_sovits` in `config/config.yaml` with valid `base_url`, `ref_audio_path`, `prompt_text`, and `prompt_lang`
- **THEN** the system SHALL send a POST request to `{base_url}/tts` with the request text and configured parameters
- **THEN** the system SHALL return WAV audio bytes containing the synthesized speech

#### Scenario: Synthesize speech with non-default reference audio

- **WHEN** the TTS `synthesize()` method is called with custom `ref_audio_path`, `prompt_text`, or `prompt_lang` via kwargs
- **THEN** the system SHALL use the provided parameters instead of the configured defaults

#### Scenario: GPT-SoVITS server unavailable

- **WHEN** the GPT-SoVITS server is not running or unreachable
- **THEN** the system SHALL log an error and raise an appropriate exception
- **THEN** the TTS node SHALL fall back gracefully (return None for tts_audio)

#### Scenario: Invalid parameters returned by server

- **WHEN** the GPT-SoVITS API returns an HTTP 400 error with a JSON error body
- **THEN** the system SHALL log the error details
- **THEN** the system SHALL raise an exception with the error message from the server

### Requirement: Configuration schema

The system SHALL support the following configuration parameters for the `gpt_sovits` provider:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | str | `"http://127.0.0.1:9880"` | GPT-SoVITS API server URL |
| `ref_audio_path` | str | (required) | Path to reference audio file on the server |
| `prompt_text` | str | (required) | Transcript of the reference audio |
| `prompt_lang` | str | `"zh"` | Language of the prompt text |
| `text_lang` | str | `"zh"` | Language of the text to synthesize |
| `top_k` | int | `15` | Top-k sampling parameter |
| `top_p` | float | `1.0` | Top-p sampling parameter |
| `temperature` | float | `1.0` | Temperature for sampling |
| `speed` | float | `1.0` | Speed factor (speed_factor in GPT-SoVITS API) |
| `media_type` | str | `"wav"` | Audio output format (`wav`, `ogg`, `aac`, `raw`) |
| `streaming_mode` | bool | `false` | Enable streaming mode |
| `text_split_method` | str | `"cut5"` | Text segmentation method |
| `sample_steps` | int | `32` | Sampling steps for V3/V4 models |
| `seed` | int | `-1` | Random seed (-1 for random) |

#### Scenario: Default configuration works

- **WHEN** the user configures only the required parameters (`base_url`, `ref_audio_path`, `prompt_text`)
- **THEN** the system SHALL use sensible defaults for all other parameters

#### Scenario: All configuration parameters passed correctly

- **WHEN** the user provides all optional parameters in `services.yaml`
- **THEN** each parameter SHALL be passed to the GPT-SoVITS API request in the correct field name

### Requirement: Service lifecycle

The TTS service SHALL properly manage its HTTP client lifecycle.

#### Scenario: Client initialization

- **WHEN** the TTS service is instantiated
- **THEN** an `httpx.AsyncClient` SHALL be created with the configured `base_url` as base URL

#### Scenario: Client cleanup

- **WHEN** `close()` is called on the TTS service
- **THEN** the HTTP client SHALL be properly closed to release connections
