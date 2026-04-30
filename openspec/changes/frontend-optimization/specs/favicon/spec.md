## ADDED Requirements

### Requirement: Browser displays a project favicon
The frontend SHALL serve a favicon so the browser tab shows a recognizable icon instead of a blank page.

#### Scenario: Tab icon visible
- **WHEN** user opens the app in a browser
- **THEN** the browser tab SHALL display the Anima favicon

#### Scenario: Dark/light mode adaptation
- **WHEN** the browser's color scheme is dark or light
- **THEN** the favicon SHALL adapt to provide good visibility (SVG media query)
