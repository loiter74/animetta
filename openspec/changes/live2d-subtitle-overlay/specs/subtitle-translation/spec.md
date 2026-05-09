## ADDED Requirements

### Requirement: Backend LLM translates response text
After the LLM generates a response, the system SHALL translate the response text to the configured target language using the same LLM provider, before emitting socket events.

#### Scenario: Translation succeeds
- **WHEN** a response is generated and translation is enabled
- **THEN** the system SHALL call the LLM with a translation prompt requesting conversion from source_language to target_language
- **THEN** the translated text SHALL be included in the `sentence` socket event as a `translation` field

#### Scenario: Translation fails
- **WHEN** the LLM translation call fails or times out
- **THEN** the system SHALL emit the sentence event without the `translation` field
- **THEN** the error SHALL be logged but SHALL NOT block the response pipeline

#### Scenario: Translation disabled
- **WHEN** translation is disabled in config
- **THEN** the system SHALL skip the translation step
- **THEN** the `sentence` event SHALL be emitted without a `translation` field

### Requirement: Translation prompt is configurable
The system SHALL use a configurable system prompt for the translation LLM call, defaulting to a neutral translation instruction.

#### Scenario: Default translation behavior
- **WHEN** the LLM translates a response
- **THEN** the prompt SHALL instruct the LLM to "Translate the following text from {source_language} to {target_language}. Output only the translation, no explanations."

#### Scenario: Custom prompt override
- **WHEN** a custom translation prompt is provided in config
- **THEN** the system SHALL use the custom prompt instead of the default

### Requirement: Sentence event carries translation data
The `sentence` Socket.IO event payload SHALL be extended with optional `translation` and `lang` fields.

#### Scenario: Original text emission
- **WHEN** the response text is ready (before or without translation)
- **THEN** the system SHALL emit `sentence` with `{text: "你好", seq: 0, lang: "zh"}`

#### Scenario: Translation emission
- **WHEN** translation completes
- **THEN** the system SHALL emit `sentence` with `{text: "你好", seq: 0, translation: "Hello", lang: "zh", target_lang: "en"}`

### Requirement: Frontend receives translation via socket
The frontend SHALL listen for the `translation` field in `sentence` events and provide it to the subtitle overlay.

#### Scenario: New composable extracts translation
- **WHEN** a `sentence` event arrives with a `translation` field
- **THEN** the `useSubtitle` composable SHALL store both `text` and `translation` as reactive refs
- **THEN** the subtitle overlay SHALL display according to current display mode

### Requirement: Translation target can be updated at runtime
The backend SHALL accept a `translation.configure` socket event from the frontend to update the target language without restart.

#### Scenario: Runtime language change
- **WHEN** the backend receives `translation.configure` with `{target_language: "日本語"}`
- **THEN** the backend SHALL update the active translation target language
- **THEN** subsequent responses SHALL be translated to the new language

#### Scenario: Config persists for session
- **WHEN** the target language is updated via socket event
- **THEN** the change SHALL remain active until the server restarts or is changed again
