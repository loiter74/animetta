## ADDED Requirements

### Requirement: AI responds to each danmaku
When a danmaku is received, the system SHALL send it through the LangGraph orchestrator for AI processing. Each danmaku triggers an independent response.

#### Scenario: Single danmaku triggers AI
- **WHEN** a danmaku is dequeued for processing
- **THEN** the system SHALL call `orchestrator.process_text()` with the danmaku text as input
- **THEN** the AI SHALL generate a response as if the viewer said the danmaku aloud
- **THEN** the system SHALL emit `danmaku.ai_reply` Socket.IO event with `{danmaku_text, reply_text, user_name}`

#### Scenario: Sequential processing
- **WHEN** danmaku arrive faster than AI can respond
- **THEN** each danmaku SHALL be queued and processed sequentially (FIFO)
- **THEN** the next danmaku SHALL only be processed after the current response completes

### Requirement: Draggable AI caption bar
The system SHALL display AI's responses to danmaku in a draggable caption/subtitle bar overlay, separate from the danmaku stream.

#### Scenario: Caption bar display
- **WHEN** AI responds to a danmaku
- **THEN** a caption bar SHALL appear at the bottom of the screen
- **THEN** it SHALL display `AI: {reply_text}` with character name prefix
- **THEN** it SHALL auto-hide after 8 seconds

#### Scenario: Draggable positioning
- **WHEN** user drags the caption bar
- **THEN** it SHALL follow the mouse/finger position
- **THEN** position SHALL be constrained within viewport bounds
- **THEN** position SHALL persist during the session (no localStorage persistence needed for simple implementation)

#### Scenario: Multiple captions
- **WHEN** a new AI response arrives while a caption is still visible
- **THEN** the existing caption SHALL be replaced with the new one (no stacking)

### Requirement: Dedicated Socket.IO events for danmaku AI flow
The system SHALL use separate Socket.IO events for danmaku-related communication to avoid mixing with the main chat flow.

#### Scenario: Event contract
- **WHEN** danmaku is received from Bilibili
- **THEN** server emits `danmaku` with `{text, user_name, user_id, timestamp}`
- **WHEN** AI finishes responding to a danmaku
- **THEN** server emits `danmaku.ai_reply` with `{danmaku_text, reply_text, user_name, character_name}`
- **WHEN** connection status changes
- **THEN** server emits `danmaku.status` with `{connected: bool, error?: string}`
