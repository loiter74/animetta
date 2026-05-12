## ADDED Requirements

### Requirement: Live2DActionQueue operations
Live2DActionQueue SHALL correctly manage action enqueue/dequeue with various policies.

#### Scenario: APPEND policy adds to end
- **WHEN** action is enqueued with APPEND policy
- **THEN** it SHALL be added to the end of the queue

#### Scenario: REPLACE policy replaces current
- **WHEN** action is enqueued with REPLACE policy
- **THEN** it SHALL replace the current executing action

#### Scenario: INTERRUPT policy clears and enqueues
- **WHEN** action is enqueued with INTERRUPT policy
- **THEN** it SHALL clear the queue then add the new action

#### Scenario: DROP_OLDEST policy respects max size
- **WHEN** queue is full and DROP_OLDEST is set
- **THEN** it SHALL drop the oldest action to make room

#### Scenario: DROP_NEWEST policy rejects new actions
- **WHEN** queue is full and DROP_NEWEST is set
- **THEN** it SHALL reject the new action

#### Scenario: dequeue returns next action
- **WHEN** dequeue() is called
- **THEN** it SHALL return the next action and remove it from queue

#### Scenario: ActionFactory creates typed actions
- **WHEN** ActionFactory.expression() is called with parameters
- **THEN** it SHALL return an expression action
- **WHEN** ActionFactory.motion() is called
- **THEN** it SHALL return a motion action

### Requirement: VisemeLipSync processing
VisemeLipSync SHALL correctly analyze audio for mouth parameter generation.

#### Scenario: FFT produces frequency bands
- **WHEN** process_audio() is called with audio bytes
- **THEN** it SHALL produce 5-band spectral analysis

#### Scenario: viseme weights map to mouth parameters
- **WHEN** audio is processed
- **THEN** ParamMouthOpenY and ParamMouthForm SHALL be computed

#### Scenario: SimpleLipSync fallback works
- **WHEN** SimpleLipSync processes audio
- **THEN** it SHALL produce mouth parameters based on RMS

#### Scenario: Factory creates correct engine type
- **WHEN** create_lip_sync_engine("viseme") is called
- **THEN** it SHALL return a VisemeLipSync instance
- **WHEN** create_lip_sync_engine("simple") is called
- **THEN** it SHALL return a SimpleLipSync instance

### Requirement: PresetLoader functionality
PresetLoader SHALL load and create Live2D action presets from YAML configuration.

#### Scenario: create_emote_action builds emotion preset
- **WHEN** create_emote_action() is called with emotion name
- **THEN** it SHALL return a parameter action with correct values

#### Scenario: create_gesture_action builds gesture
- **WHEN** create_gesture_action() is called with gesture name
- **THEN** it SHALL return a motion action

#### Scenario: create_react_action builds reaction
- **WHEN** create_react_action() is called with reaction name
- **THEN** it SHALL return a sequence action
