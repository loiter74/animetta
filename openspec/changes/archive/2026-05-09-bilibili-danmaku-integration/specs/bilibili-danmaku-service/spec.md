## ADDED Requirements

### Requirement: Connect to Bilibili live room
The system SHALL connect to a Bilibili live room using `bilibili-api-python`'s `LiveDanmaku` class and receive real-time danmaku messages.

#### Scenario: Connect to live room
- **WHEN** the backend starts with `bilibili.enabled: true` and a valid `room_id`
- **THEN** the system SHALL establish a WebSocket connection to Bilibili's danmaku server
- **THEN** the system SHALL emit `danmaku.status` with `{connected: true}`

#### Scenario: Connection failure
- **WHEN** the connection to Bilibili fails (invalid room_id or network error)
- **THEN** the system SHALL retry with exponential backoff (max 5 retries)
- **THEN** the system SHALL emit `danmaku.status` with `{connected: false, error: "..."}`

### Requirement: Receive and parse danmaku events
The system SHALL receive `DANMU_MSG` events from Bilibili and extract message content, user name, and user ID.

#### Scenario: Parse danmaku message
- **WHEN** a `DANMU_MSG` event is received
- **THEN** the system SHALL extract `text` (弹幕内容), `user_name` (发送者昵称), `user_id` (发送者UID)
- **THEN** the system SHALL emit `danmaku` Socket.IO event with `{text, user_name, user_id, timestamp}`

#### Scenario: Parse gift event
- **WHEN** a `SEND_GIFT` event is received
- **THEN** the system SHALL emit `danmaku` event with formatted gift text

### Requirement: Danmaku queue management
The system SHALL maintain an internal queue of received danmaku messages for sequential processing.

#### Scenario: Queue danmaku
- **WHEN** a danmaku is received and AI is currently processing another
- **THEN** the danmaku SHALL be queued in an `asyncio.Queue`
- **THEN** it SHALL be processed in FIFO order after current processing completes

#### Scenario: Queue overflow
- **WHEN** the queue exceeds 100 messages
- **THEN** the oldest messages SHALL be dropped (FIFO eviction)

### Requirement: Thread-safe async operation
The Bilibili service SHALL run on a separate event loop in a worker thread to avoid blocking the main asyncio event loop.

#### Scenario: Start in worker thread
- **WHEN** the server starts
- **THEN** `BilibiliDanmakuService` SHALL start in a thread with `asyncio.new_event_loop()`
- **THEN** cross-thread communication SHALL use `asyncio.Queue` or `call_soon_threadsafe`

### Requirement: Lifecycle management
The system SHALL properly start/stop the Bilibili service with the server lifecycle.

#### Scenario: Graceful shutdown
- **WHEN** the server stops
- **THEN** the Bilibili connection SHALL be disconnected gracefully
- **THEN** all pending queued messages SHALL be discarded with a warning log
