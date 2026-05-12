## ADDED Requirements

### Requirement: BilibiliDanmaku connection lifecycle
BilibiliDanmaku SHALL handle connection lifecycle with proper state management.

#### Scenario: connect establishes WebSocket
- **WHEN** connect() is called with room_id
- **THEN** it SHALL establish a Bilibili WebSocket connection

#### Scenario: disconnect cleans up
- **WHEN** disconnect() is called
- **WHEN** it SHALL close the WebSocket and clean up resources

#### Scenario: reconnect with backoff
- **WHEN** connection drops unexpectedly
- **THEN** it SHALL attempt reconnection with exponential backoff

### Requirement: BilibiliDanmaku message handling
BilibiliDanmaku SHALL parse and forward danmaku messages.

#### Scenario: on_danmaku fires callback
- **WHEN** a danmaku message is received
- **THEN** it SHALL call the registered danmaku callback

#### Scenario: heartbeat keeps connection alive
- **WHEN** connected
- **THEN** it SHALL send heartbeat packets at configured intervals
