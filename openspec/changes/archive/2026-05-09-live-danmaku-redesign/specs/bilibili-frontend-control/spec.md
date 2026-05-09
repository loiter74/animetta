## ADDED Requirements

### Requirement: Frontend-initiated Bilibili connection
The backend SHALL expose Socket.IO event handlers that allow the frontend to start, stop, and reconfigure the Bilibili danmaku connection in real time.

#### Scenario: Connect from frontend
- **WHEN** server receives `bilibili.connect` event with `{room_id: number}`
- **THEN** the backend SHALL start the `BilibiliDanmakuService` with the given room_id
- **THEN** the backend SHALL emit `danmaku.status` with `{connected: true, message: "Connected"}`
- **THEN** if already connected, the backend SHALL disconnect first then connect to the new room

#### Scenario: Disconnect from frontend
- **WHEN** server receives `bilibili.disconnect` event
- **THEN** the backend SHALL stop the `BilibiliDanmakuService` gracefully
- **THEN** the backend SHALL emit `danmaku.status` with `{connected: false, message: "Disconnected"}`

#### Scenario: Update room ID from frontend
- **WHEN** server receives `bilibili.update_room` event with `{room_id: number}`
- **THEN** the backend SHALL stop the current `BilibiliDanmakuService` if running
- **THEN** the backend SHALL start a new `BilibiliDanmakuService` with the updated room_id
- **THEN** the backend SHALL emit `danmaku.status` with `{connected: true, message: "Connected to new room"}`

#### Scenario: Connection error reporting
- **WHEN** the `BilibiliDanmakuService` fails to connect or loses connection
- **THEN** the backend SHALL emit `danmaku.status` with `{connected: false, message: "<error description>"}`
- **THEN** the settings panel SHALL display the error message to the user

#### Scenario: Initial connection from server config
- **WHEN** server starts and `bilibili_config` contains `enabled: true` with a `room_id`
- **THEN** the backend SHALL automatically start the `BilibiliDanmakuService` at startup
- **THEN** this SHALL respect the `bilibili.connect` / `bilibili.disconnect` events for subsequent changes
