## ADDED Requirements

### Requirement: Chat store is tested
The chat store (frontend/src/stores/chat.ts) SHALL have unit tests covering all actions and state transitions.

#### Scenario: Send message adds to messages array
- **WHEN** chat store's sendMessage action is called with text content
- **THEN** the messages array SHALL contain the new message
- **THEN** the new message SHALL have correct sender and content fields

#### Scenario: Clear messages resets state
- **WHEN** clearMessages action is called
- **THEN** messages array SHALL be empty

#### Scenario: Streaming text appends to last message
- **WHEN** appendToLastMessage is called with text chunks
- **THEN** the last message content SHALL be updated with appended text

### Requirement: Settings store is tested
The settings store (frontend/src/stores/settings.ts) SHALL have unit tests covering provider selection and UI preferences.

#### Scenario: LLM provider selection updates state
- **WHEN** setLlmProvider is called with a provider name
- **THEN** the store SHALL reflect the new provider value

#### Scenario: Persisted settings survive reset
- **WHEN** settings are saved and the store is re-initialized
- **THEN** persisted settings SHALL be restored

### Requirement: Live2D store is tested
The Live2D store (frontend/src/stores/live2d.ts) SHALL have unit tests covering expression and motion state.

#### Scenario: Expression change updates current expression
- **WHEN** setExpression is called with an expression name
- **THEN** currentExpression SHALL match the given name

#### Scenario: Motion queue enqueues correctly
- **WHEN** enqueueMotion is called with a motion ID
- **THEN** the motion queue SHALL contain the motion
