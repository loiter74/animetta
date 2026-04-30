## ADDED Requirements

### Requirement: User can set a custom background image
The frontend SHALL allow users to personalize the app background with a custom image via URL input, file upload, or preset selection. The setting SHALL persist across page reloads via localStorage.

#### Scenario: Select a preset background
- **WHEN** user clicks a preset background thumbnail in settings
- **THEN** the app background SHALL change to that image immediately
- **AND** the selection SHALL persist after page refresh

#### Scenario: Set background via URL
- **WHEN** user enters an image URL and confirms
- **THEN** the app background SHALL display that image
- **AND** invalid URLs SHALL show an error message without changing the background

#### Scenario: Upload a custom image
- **WHEN** user selects an image file (≤5MB)
- **THEN** the app background SHALL display the uploaded image
- **AND** files exceeding 5MB SHALL show an error

#### Scenario: Clear custom background
- **WHEN** user clicks "移除背景" button
- **THEN** the background SHALL revert to the default solid color
