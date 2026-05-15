## ADDED Requirements

### Requirement: Model lifecycle events SHALL be dispatched without unawaited coroutine warnings
The system SHALL emit `model_status` events via Socket.IO during model loading lifecycle (loading/loaded/error) without producing `RuntimeWarning: coroutine was never awaited`.

#### Scenario: Status emission during synchronous registration
- **WHEN** a model is registered with a synchronous loader in `ModelLoadingManager.register()`
- **THEN** the `model_status` event SHALL be emitted without producing an unawaited coroutine warning

#### Scenario: Status emission during async warmup
- **WHEN** `ModelLoadingManager._load_one()` transitions a model's state (loading → loaded/error)
- **THEN** the `model_status` event SHALL be emitted without producing an unawaited coroutine warning

#### Scenario: Socket.IO failure is never fatal
- **WHEN** the `model_status` emit raises an exception (Socket.IO not available, connection closed)
- **THEN** the exception SHALL be caught and logged at DEBUG level, without affecting model loading
- **AND** the model's `ModelSlot` state SHALL still be updated
