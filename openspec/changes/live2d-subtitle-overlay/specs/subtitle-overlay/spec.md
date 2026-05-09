## ADDED Requirements

### Requirement: Subtitle overlay renders at bottom of Live2D canvas
The system SHALL display a subtitle overlay component positioned at the bottom-center of the Live2D canvas area, rendered as an absolutely-positioned child of the Live2DRenderer container.

#### Scenario: Subtitle visible on conversation response
- **WHEN** the AI generates a response text and the subtitle is enabled
- **THEN** the subtitle overlay SHALL appear at the bottom of the Live2D canvas
- **THEN** the subtitle SHALL display the AI's response text

#### Scenario: Subtitle hidden when idle
- **WHEN** there is no active conversation (no response being generated)
- **THEN** the subtitle overlay SHALL be hidden or fully faded out

### Requirement: Subtitle entrance/exit animation
The subtitle SHALL animate in with a spring-bounce pop-in effect (CSS cubic-bezier overshoot easing) and animate out with a smooth fade.

#### Scenario: Pop-in entrance
- **WHEN** a new response text arrives
- **THEN** the subtitle SHALL animate from `translateY(20px)` to `translateY(0)` with opacity 0 → 1 using `cubic-bezier(0.34, 1.56, 0.64, 1)` easing over ~400ms

#### Scenario: Fade-out exit
- **WHEN** the response ends (conversation-end signal received)
- **THEN** the subtitle SHALL fade out with opacity 1 → 0 over ~300ms

### Requirement: Subtitle supports bilingual display
The subtitle SHALL support three display modes: original only, translation only, and bilingual (both).

#### Scenario: Bilingual mode layout
- **WHEN** display mode is set to "bilingual" and both original text and translation are available
- **THEN** the original text SHALL be displayed in a larger font (1.2rem) above
- **THEN** the translated text SHALL be displayed in a smaller font (0.95rem) below
- **THEN** the two texts SHALL be visually distinct (different opacity or color tone)

#### Scenario: Original-only mode
- **WHEN** display mode is set to "original"
- **THEN** only the original language text SHALL be shown

#### Scenario: Translation-only mode
- **WHEN** display mode is set to "translated" and translation is available
- **THEN** only the translated text SHALL be shown

### Requirement: Subtitle overlay does not block mouse interaction
The subtitle overlay SHALL use `pointer-events: none` so mouse events pass through to the Live2D canvas.

#### Scenario: Click-through subtitle
- **WHEN** the user clicks or drags on the Live2D canvas area covered by the subtitle
- **THEN** the interaction SHALL reach the Live2D model (drag, focus) without interference from the subtitle overlay

### Requirement: Subtitle visual style matches anime theme
The subtitle SHALL use the existing design system tokens: glassmorphism background, pink accent color, rounded corners, and appropriate typography.

#### Scenario: Default appearance
- **WHEN** the subtitle is displayed
- **THEN** it SHALL have a semi-transparent `bg-c-surface/70 backdrop-blur-xl` background
- **THEN** it SHALL have `rounded-2xl` corners and `border border-c-border` border
- **THEN** the text SHALL use `text-c-text` color with accent pink decorative elements
- **THEN** the maximum width SHALL be `80vw` with horizontal centering
