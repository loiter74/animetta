## ADDED Requirements

### Requirement: Dedicated danmaku stream page
The system SHALL provide a dedicated page at route `/danmaku` showing a Twitch-style scrolling chat stream of Bilibili live danmaku.

#### Scenario: Navigate to danmaku page
- **WHEN** user navigates to `/danmaku`
- **THEN** a full-height chat stream SHALL be displayed
- **THEN** the page SHALL NOT show AI responses, only raw danmaku from Bilibili

#### Scenario: Danmaku flow direction
- **WHEN** a new danmaku arrives via the `danmaku` Socket.IO event
- **THEN** it SHALL appear at the **bottom** of the chat stream
- **THEN** existing messages SHALL scroll upward (Twitch style, NOT right-to-left flying)
- **THEN** the stream SHALL auto-scroll to the newest message

### Requirement: Danmaku message display
Each danmaku message SHALL display the user name and message text with clear visual hierarchy.

#### Scenario: Message format
- **WHEN** a danmaku is displayed
- **THEN** it SHALL show `[用户名]: 消息内容` format
- **THEN** the user name SHALL be styled with accent color (`c-accent`)
- **THEN** message text SHALL be styled with primary text color (`c-text`)

#### Scenario: Same-user grouping
- **WHEN** consecutive messages from the same user appear within 5 seconds
- **THEN** they MAY be grouped under a single user name display

### Requirement: Connection status indicator
The page SHALL show real-time Bilibili connection status.

#### Scenario: Status display
- **WHEN** `danmaku.status` event fires with `connected: true`
- **THEN** a green "● 已连接" indicator SHALL be shown
- **WHEN** `danmaku.status` event fires with `connected: false`
- **THEN** a red "● 已断开" indicator SHALL be shown

### Requirement: Message limit and performance
The page SHALL maintain performance with high-volume danmaku streams.

#### Scenario: Message cap
- **WHEN** total messages exceed 500
- **THEN** the oldest messages SHALL be removed to keep at most 500 in the DOM

#### Scenario: Virtual scrolling (future)
- **WHEN** danmaku rate exceeds 10 messages/second
- **THEN** the browser SHALL remain responsive (may use virtual scrolling in future iteration)

### Requirement: Danmaku store
The system SHALL have a dedicated Pinia store for danmaku state.

#### Scenario: Store structure
- **WHEN** a danmaku is received
- **THEN** the `danmaku` store SHALL append it to the `messages` array
- **THEN** store fields SHALL include: `messages[]`, `connected`, `messageCount`
