## ADDED Requirements

### Requirement: Subtitle toggle in Settings panel
The SettingsPanel SHALL contain a "字幕" (Subtitle) configuration section with an enable/disable toggle.

#### Scenario: Enable subtitle
- **WHEN** the user toggles the subtitle switch to ON in SettingsPanel
- **THEN** the subtitle overlay SHALL appear on subsequent AI responses
- **THEN** the preference SHALL be persisted in localStorage

#### Scenario: Disable subtitle
- **WHEN** the user toggles the subtitle switch to OFF
- **THEN** the subtitle overlay SHALL be hidden immediately
- **THEN** the preference SHALL be persisted in localStorage

### Requirement: Display mode selector
The SettingsPanel SHALL provide a selector for the subtitle display mode with three options: "原文" (original), "翻译" (translated), "双语" (bilingual).

#### Scenario: Change display mode
- **WHEN** the user selects a different display mode
- **THEN** the subtitle SHALL immediately reflect the new mode on the current text
- **THEN** the preference SHALL be persisted in localStorage

### Requirement: Font size setting
The SettingsPanel SHALL provide a font size selector for the subtitle text (small/medium/large).

#### Scenario: Adjust font size
- **WHEN** the user selects a different font size
- **THEN** the subtitle text SHALL resize accordingly
- **THEN** the preference SHALL be persisted in localStorage

### Requirement: Target language configuration
The SettingsPanel SHALL allow the user to select the target translation language, which is sent to the backend via a socket event.

#### Scenario: Change target language
- **WHEN** the user selects a new target language (e.g., "English" → "日本語")
- **THEN** the frontend SHALL emit a `translation.configure` socket event with `{target_language: "日本語"}`
- **THEN** the backend SHALL update the translation target for subsequent responses
- **THEN** the preference SHALL be persisted in localStorage

### Requirement: Subtitle config is persisted
The subtitle configuration SHALL survive page reloads via localStorage.

#### Scenario: Config persists across sessions
- **WHEN** the user configures subtitle settings and reloads the page
- **THEN** the subtitle SHALL restore all settings (enabled, display mode, font size, target language)
