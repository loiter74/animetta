## ADDED Requirements

### Requirement: Subtitle visibility duration SHALL be driven by audio playback duration

The subtitle overlay SHALL remain visible until the TTS audio playback is complete, rather than being dismissed by a fixed timeout after text arrival.

When audio data arrives via `audio_with_expression`, the system SHALL estimate the audio duration from the data payload and schedule subtitle dismissal accordingly, with a safety buffer to ensure the subtitle does not disappear before audio finishes.

#### Scenario: Normal conversation flow — subtitle stays visible through audio playback

- **WHEN** backend sends `sentence(is_complete=true)`
- **AND** backend subsequently sends `audio_with_expression` with audio data
- **THEN** the subtitle SHALL remain visible for the estimated audio duration + safety buffer
- **AND** the subtitle SHALL NOT disappear before the `audio_with_expression` event is processed

#### Scenario: Audio duration is shorter than 3 seconds

- **WHEN** estimated audio duration is less than 3 seconds
- **THEN** the subtitle SHALL remain visible for at least 3 seconds (minimum floor)

#### Scenario: User sends interrupt signal

- **WHEN** backend sends `stop_audio` event
- **THEN** the subtitle SHALL be scheduled to hide after 1.5 seconds (existing behavior preserved)

#### Scenario: Translation arrives while subtitle is visible

- **WHEN** backend sends `subtitle.translation` event while subtitle is visible
- **THEN** the subtitle SHALL reset its hide timer to 6 seconds (existing behavior preserved)

#### Scenario: Audio data is empty or malformed

- **WHEN** `audio_with_expression` contains no valid audio data
- **THEN** the subtitle SHALL fall back to a minimum 3-second visibility
- **AND** the system SHALL NOT crash or produce console errors
