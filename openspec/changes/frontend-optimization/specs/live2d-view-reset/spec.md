## ADDED Requirements

### Requirement: User can reset Live2D view to default
The frontend SHALL provide a button that resets the Live2D model's zoom level to 1x and re-centers its position.

#### Scenario: Reset view button works
- **WHEN** user clicks "重置视图" button after zooming or dragging the Live2D model
- **THEN** the model SHALL return to default zoom (1x) and center position

#### Scenario: Reset available when model loaded
- **WHEN** a Live2D model is loaded and visible
- **THEN** the reset button SHALL be accessible in the settings panel or Live2D controls area
