## ADDED Requirements

### Requirement: Audio effects pipeline applies after TTS synthesis
The system SHALL apply a SoX-based audio effects pipeline to the synthesized audio before returning from `KokoroTTS.synthesize()` when GLaDOS effects are enabled.

#### Scenario: Effects applied to raw audio
- **WHEN** `KokoroTTS.synthesize("你好")` is called with `glados_effect.enabled: true`
- **THEN** the returned audio has been processed through the SoX effects chain
- **AND** the audio duration and sample rate are preserved

#### Scenario: Effects disabled returns raw audio
- **WHEN** `KokoroTTS.synthesize("你好")` is called with `glados_effect.enabled: false`
- **THEN** the returned audio is unprocessed Kokoro output

### Requirement: Effects chain uses SoX pipeline
The SoX effects pipeline SHALL apply the following effects in sequence: pitch shift, stretch, overdrive, chorus, bandpass, compand, gain.

#### Scenario: Default effects chain
- **WHEN** effects are enabled with default parameters
- **THEN** audio is processed through `pitch -300` → `stretch 1.05` → `overdrive 20` → `chorus 0.7 0.9 55 0.4 0.25 2 -t` → `bandpass 300 3` → `compand 0.3,1 6:-70,-60,-20 -5 -90 0.2` → `gain -3`
- **AND** the output has audible electronic/robotic characteristics

#### Scenario: Effects chain parameters are configurable
- **WHEN** config specifies custom effect parameters
- **THEN** the SoX pipeline uses the configured values instead of defaults

### Requirement: Effects processing handles edge cases
The effects pipeline SHALL handle various input conditions gracefully.

#### Scenario: Empty or very short audio
- **WHEN** synthesized audio is empty or < 100ms
- **THEN** effects pipeline skips processing and returns raw audio
- **AND** logs a warning

#### Scenario: Error during effects processing
- **WHEN** SoX effects processing fails (e.g., corrupt audio)
- **THEN** the system falls back to returning raw Kokoro audio
- **AND** logs the error but does not crash

### Requirement: Effects are implemented as standalone module
The SoX effects logic SHALL be encapsulated in a reusable `GladosEffectProcessor` class with `async process(audio_bytes: bytes) -> bytes`.

#### Scenario: Module is reusable
- **WHEN** `GladosEffectProcessor` is instantiated with params
- **THEN** it can process any WAV audio bytes, independent of KokoroTTS
- **AND** the `process()` method is async

### Requirement: SoX dependency check on init
The system SHALL verify SoX availability when creating the `GladosEffectProcessor`.

#### Scenario: SoX not installed
- **WHEN** `GladosEffectProcessor` is created and SoX is not found
- **THEN** it logs a clear installation error message
- **AND** sets a flag to bypass effects processing
