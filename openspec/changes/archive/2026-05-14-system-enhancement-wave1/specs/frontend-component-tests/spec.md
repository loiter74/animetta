## ADDED Requirements

### Requirement: Chat components are tested
All chat UI components (frontend/src/components/chat/) SHALL have rendering and interaction tests.

#### Scenario: Chat bubble renders message content
- **WHEN** the chat bubble component receives a message prop
- **THEN** it SHALL display the message text

#### Scenario: Chat input emits on submit
- **WHEN** user types text and presses Enter
- **THEN** the component SHALL emit a submit event with the text content

#### Scenario: Streaming indicator shows during active stream
- **WHEN** streaming is active (isStreaming prop is true)
- **THEN** the streaming indicator SHALL be visible

### Requirement: Live2D renderer component is tested
The Live2D renderer (frontend/src/components/live2d/) SHALL have basic rendering tests with the canvas element.

#### Scenario: Canvas element exists
- **WHEN** Live2DRenderer is mounted
- **THEN** a canvas element SHALL exist in the rendered output

### Requirement: Layout components are tested
Layout components (sidebar, panels) SHALL be tested for correct rendering.

#### Scenario: Sidebar renders navigation items
- **WHEN** Sidebar component is mounted
- **THEN** navigation buttons SHALL be rendered

#### Scenario: Panel toggles visibility
- **WHEN** a panel's visibility prop changes
- **THEN** the panel SHALL show or hide accordingly
