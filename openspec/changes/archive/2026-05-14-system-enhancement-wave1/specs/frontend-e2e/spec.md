## ADDED Requirements

### Requirement: Chat conversation flow works end-to-end
The Playwright E2E test SHALL verify the complete chat flow from input to response display.

#### Scenario: User sends a chat message
- **WHEN** user types text in the chat input
- **WHEN** user clicks send button
- **THEN** the message SHALL appear in the chat history
- **THEN** there SHALL be no console errors

### Requirement: Settings page renders correctly
The Playwright E2E test SHALL navigate to the settings page and verify it loads.

#### Scenario: Navigate to settings
- **WHEN** user clicks the Settings navigation button
- **THEN** the settings page SHALL render
- **THEN** provider selection controls SHALL be visible

### Requirement: Application loads without errors
The Playwright E2E test SHALL verify the initial page load has no console errors.

#### Scenario: Initial page load
- **WHEN** the application loads at `/`
- **THEN** the page title SHALL be "Anima Desktop"
- **THEN** the app SHALL mount with visible content
- **THEN** console error count SHALL be zero
