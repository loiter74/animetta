## ADDED Requirements

### Requirement: Live chat panel in right-side dialog
The system SHALL provide a live chat panel as a new "直播" tab in the right-side InteractivePanel, showing Bilibili danmaku messages with animated pop-in appearance.

#### Scenario: Navigate to live chat tab
- **WHEN** user clicks the "直播" tab button in InteractivePanel
- **THEN** the panel SHALL display the live chat view with danmaku messages
- **THEN** the panel SHALL show connection status indicator (connected/disconnected)

#### Scenario: Danmaku appears with pop-in animation
- **WHEN** a new danmaku is received via the `danmaku` Socket.IO event
- **THEN** the danmaku SHALL appear in the live chat panel with a pop-in animation (translateY + opacity)
- **THEN** danmaku messages SHALL appear one at a time, in chronological order
- **THEN** the panel SHALL auto-scroll to show the newest message

#### Scenario: Empty state when no messages
- **WHEN** the live chat panel is active but no danmaku have been received
- **THEN** the panel SHALL show an empty state message ("等待弹幕中...")
- **THEN** if disconnected, the panel SHALL show a warning indicator

#### Scenario: AI replies visible in chat
- **WHEN** a `danmaku.ai_reply` event is received
- **THEN** the system SHALL create an assistant ChatMessage in the chat store
- **THEN** the message SHALL appear in the main ChatPanel message list under "聊天" tab
- **THEN** the message text SHALL be prefixed with the original danmaku context (e.g., "回复 @username: reply_text")

### Requirement: Message limit and performance
The live chat panel SHALL maintain performance with high-volume danmaku streams.

#### Scenario: Message cap enforced
- **WHEN** danmaku messages exceed 500 in the store
- **THEN** the oldest messages SHALL be evicted, keeping only the most recent 500

#### Scenario: High-volume handling
- **WHEN** danmaku arrive at high frequency (10+ messages/second)
- **THEN** each message SHALL still appear with its pop-in animation
- **THEN** the UI SHALL remain responsive with no jank
