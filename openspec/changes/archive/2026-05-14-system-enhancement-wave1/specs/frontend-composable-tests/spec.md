## ADDED Requirements

### Requirement: useLive2D composable is tested
The useLive2D composable (frontend/src/components/live2d/useLive2D.ts) SHALL have unit tests for its core logic functions.

#### Scenario: centerModel initializes scale correctly
- **WHEN** centerModel is called with valid baseBounds
- **THEN** it SHALL set scale without calling getBounds()

#### Scenario: handleResize preserves drag offset
- **WHEN** handleResize is called after a drag
- **THEN** model position SHALL NOT be reset to center
- **THEN** scale SHALL remain unchanged
