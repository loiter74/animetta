## ADDED Requirements

### Requirement: Live room ID configuration in settings
The system SHALL provide a live stream configuration section in the frontend Settings panel for real-time room ID input and connection control.

#### Scenario: Room ID input field
- **WHEN** user opens the Settings panel
- **THEN** the panel SHALL display a "直播设置" section with a room ID input field
- **THEN** the room ID field SHALL accept numeric Bilibili room IDs
- **THEN** the current room ID SHALL be displayed if a connection is active

#### Scenario: Connect to room
- **WHEN** user enters a valid numeric room ID and clicks "连接" (Connect)
- **THEN** the frontend SHALL emit a `bilibili.connect` Socket.IO event with `{room_id: number}`
- **THEN** the button SHALL show a loading state while connecting
- **THEN** on success, the connection status SHALL update to "已连接"

#### Scenario: Disconnect from room
- **WHEN** user clicks "断开" (Disconnect) while connected
- **THEN** the frontend SHALL emit a `bilibili.disconnect` Socket.IO event
- **THEN** the connection status SHALL update to "已断开"
- **THEN** the danmaku messages SHALL remain visible in the live chat panel

#### Scenario: Update room ID while connected
- **WHEN** user changes the room ID and confirms while already connected
- **THEN** the frontend SHALL emit a `bilibili.update_room` Socket.IO event with `{room_id: number}`
- **THEN** the backend SHALL disconnect from the old room and connect to the new room

#### Scenario: Connection status display
- **WHEN** the `danmaku.status` event is received with connection state
- **THEN** the settings panel SHALL reflect the current status (connected/disconnected/error)
- **THEN** the live chat panel header SHALL also show the connection status indicator
