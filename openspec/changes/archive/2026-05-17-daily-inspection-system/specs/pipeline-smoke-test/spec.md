# Pipeline Smoke Test

Verifies the end-to-end conversation pipeline by initiating a real Socket.IO connection, sending a test message, and collecting expected events across all 7 LangGraph nodes.

## ADDED Requirements

### Requirement: Smoke test uses real Socket.IO client

The system SHALL use a `socketio.AsyncClient` to connect to the running server at `http://localhost:12394` using `websocket` transport. It SHALL NOT use HTTP requests, pytest fixtures, or mock clients.

#### Scenario: Successful full-pipeline smoke test

- **WHEN** the smoke test connects via Socket.IO, emits a `user_message` event with `{"text": "[inspection] ping", "mode": "text"}`, and waits 15 seconds
- **THEN** the test SHALL report `"ok": true` with received event names and duration in its `CheckResult`

#### Scenario: Connection timeout

- **WHEN** the Socket.IO client cannot connect within a 5-second timeout
- **THEN** the test SHALL report `"ok": false` with `"error": "connection_timeout"` and a duration of 0

#### Scenario: Pipeline emits unexpected exception mid-flow

- **WHEN** the Socket.IO connection is established but the server raises an exception while processing the message
- **THEN** the test SHALL report `"ok": false` with `"error"` containing the exception message

### Requirement: Event collection via wildcard listener

The system SHALL register a wildcard event listener (`@sio.on("*")`) that records all event names received during the test window. It SHALL compare the set of received events against an expected set of critical pipeline events.

#### Scenario: All expected events received

- **WHEN** within 15 seconds, events `emotion_update`, `tts_audio_data`, and `transcript_complete` are received
- **THEN** the test SHALL report `"ok": true` with `detail.received` containing all received event names

#### Scenario: Missing expected events

- **WHEN** within 15 seconds, only `tts_audio_data` is received (missing `emotion_update` and `transcript_complete`)
- **THEN** the test SHALL report `"ok": false` with `detail.missing` listing the missing events and `detail.received` listing what was received

#### Scenario: Unexpected extra events

- **WHEN** within 15 seconds, all expected events plus an unexpected `rag_cache_hit` event are received
- **THEN** the test SHALL report `"ok": true` (all expected events received) and SHALL include `rag_cache_hit` in `detail.received` — the presence of unexpected events SHALL NOT cause failure

### Requirement: Test message isolation

The system SHALL prefix all smoke test messages with `[inspection]` to allow the Memory middleware to identify and filter them from conversation context. The test SHALL NOT leave persistent side effects visible to users.

#### Scenario: Inspection message filtered from memory

- **WHEN** a smoke test sends `{"text": "[inspection] ping"}`
- **THEN** the Memory middleware SHALL recognize the `[inspection]` prefix and exclude the message from context injection into future LLM calls

### Requirement: Smoke test timeout and resource cleanup

The system SHALL enforce a total test timeout of 20 seconds (5s connect + 15s event collection). On completion or timeout, the system SHALL call `sio.disconnect()` to release the WebSocket connection.

#### Scenario: Test exceeds total timeout

- **WHEN** the event collection phase exceeds 15 seconds without receiving all expected events
- **THEN** the test SHALL disconnect, report whatever events were received up to that point, and report `"ok": false` with missing events listed
