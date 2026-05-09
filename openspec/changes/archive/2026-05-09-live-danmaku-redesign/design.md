## Context

The existing danmaku implementation was built as a "spec-driven" change (`bilibili-danmaku-integration`) with a separate `/danmaku` route page and a floating `AICaptionBar` overlay. While the backend service (`BilibiliDanmakuService`) and data flow (Socket.IO events: `danmaku`, `danmaku.status`, `danmaku.ai_reply`) work correctly, the frontend UX is disconnected from the main chat experience:

- Danmaku only visible after clicking "弹幕" button in TitleBar → navigates to separate full-page route
- No way to configure room ID without editing backend config files
- AI replies to danmaku appear in a floating overlay caption bar, not in the chat message list

The right-side `InteractivePanel` already has a tab system ("聊天" / "设置") that can be extended.

## Goals / Non-Goals

**Goals:**
- Integrate danmaku streaming into the right-side `InteractivePanel` as a new "直播" tab
- Display danmaku messages with animated "pop-in" appearance, one message at a time
- Provide real-time room ID input and connect/disconnect controls in the frontend
- AI replies to danmaku appear as assistant messages in the main chat message list
- Remove the standalone `/danmaku` route and `AICaptionBar` overlay

**Non-Goals:**
- Not changing the backend `BilibiliDanmakuService` — it works correctly
- Not changing existing Socket.IO event names (`danmaku`, `danmaku.status`, `danmaku.ai_reply`)
- Not adding multi-platform support (only Bilibili for now)
- Not implementing danmaku moderation or filtering
- Not persisting danmaku messages to history — they are ephemeral live chat

## Decisions

### Decision 1: "直播" tab in InteractivePanel vs inline in ChatPanel
**Choice**: New "直播" tab in `InteractivePanel`
**Rationale**: The existing tab system (聊天/设置) is the natural place for a third "直播" tab. This keeps the chat panel clean (regular conversation) while providing a dedicated live feed view. An inline approach would clutter the chat message list with ephemeral danmaku mixed with permanent conversation history.

### Decision 2: Danmaku appears as animated pop-in entries
**Choice**: CSS `@keyframes` pop-in animation on each danmaku entry, with a staggered appearance effect
**Rationale**: The user wants "一条消息一条消息冒出的形式" — each message should visually "pop up" one by one. A simple translateY + opacity keyframe provides this effect cleanly, similar to mobile notification toasts or live chat overlays.

### Decision 3: Live room config in Settings panel
**Choice**: Add a "直播设置" section to the existing `SettingsPanel.vue`
**Rationale**: Rather than creating a separate config component, the settings panel is the right place for configuration. This keeps the UI consistent and avoids adding another tab.

### Decision 4: New Socket.IO events for frontend control
**Choice**: Add `bilibili.connect`, `bilibili.disconnect`, `bilibili.update_room` client-to-server events
**Rationale**: Currently the Bilibili service is started at server init via `bilibili_config` in `register_routes()`. To support real-time room ID configuration, the frontend needs to be able to start/stop the service and update the room ID. New events are cleaner than overloading existing ones.

### Decision 5: AI replies go to chat message list, not AICaptionBar
**Choice**: When `danmaku.ai_reply` is received, create an assistant `ChatMessage` in the chat store
**Rationale**: The AICaptionBar was a floating overlay that auto-hides. Users want to see AI responses to danmaku as part of the permanent conversation. The existing `ChatMessage` system in `useChatStore` handles this naturally.

### Decision 6: Remove AICaptionBar and DanmakuPage entirely
**Choice**: Delete `AICaptionBar.vue`, `DanmakuPage.vue`, `DanmakuStream.vue`; remove `/danmaku` route
**Rationale**: Their functionality is fully replaced by the new "直播" tab. Keeping dead code creates confusion and maintenance burden.

### Decision 7: Keep danmaku store separate from chat store
**Choice**: `useDanmakuStore` remains independent; `useChatStore` listens for `danmaku.ai_reply`
**Rationale**: Danmaku messages are ephemeral (max 500) and structurally different from chat messages. Keeping separate stores avoids polluting chat history with live stream events. Only AI replies are bridged to the chat store.

## Risks / Trade-offs

- **[UX] New tab overload**: Adding a third tab ("直播") to InteractivePanel may feel crowded. Mitigation: The tab uses the same button pattern as existing tabs, and the live view replaces the chat input area, fitting naturally.
- **[Performance] High-volume danmaku**: Active streams can produce 50+ messages/minute. Mitigation: DanmakuStore already caps at 500 messages; the animated pop-in uses `will-change: transform` for GPU acceleration.
- **[Backend] Room ID lifecycle**: If user changes room ID while connected, the service must disconnect, reconnect to new room. Mitigation: The `bilibili.update_room` handler stops the existing service and starts a new one with the updated room ID.
- **[Removal] AICaptionBar removed**: Users who relied on the floating caption overlay lose that UI. Mitigation: The caption bar was auto-hiding and non-interactive; replacing it with permanent chat messages is strictly better.
