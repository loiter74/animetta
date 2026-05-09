## Why

The current Bilibili danmaku implementation displays messages on a separate full-page route (`/danmaku`) accessible only via the top TitleBar button, making it disconnected from the main chat experience. There is no way to configure the live room ID from the frontend — it must be set in backend config files. The user wants danmaku to feel like a live chat feed integrated into the right-side dialog panel, with real-time room configuration.

## What Changes

- **Remove** the standalone `/danmaku` route and `DanmakuPage.vue` — danmaku will no longer live on a separate page
- **Add** a "直播" (Live) tab to the `InteractivePanel` right-side dialog, alongside existing "聊天" and "设置" tabs
- **Create** a `LiveChatPanel.vue` component showing danmaku messages as animated pop-in entries, one message at a time
- **Create** a `LiveConfigPanel.vue` component (or integrate into Settings) for real-time room ID input and connect/disconnect control
- **Add** new Socket.IO events for frontend → backend: `bilibili.connect` (with room_id), `bilibili.disconnect`, `bilibili.update_room`
- **Remove** the `AICaptionBar.vue` global overlay — AI replies to danmaku will now appear in the chat message list (as assistant messages)
- **Modify** `InteractivePanel.vue` to add the "直播" tab
- **Add** backend Socket.IO event handlers for `bilibili.connect`, `bilibili.disconnect`, `bilibili.update_room`
- **Keep** existing `BilibiliDanmakuService`, `DanmakuMessage`, and `DanmakuReply` types — they work correctly
- **Keep** existing `danmaku` / `danmaku.status` / `danmaku.ai_reply` Socket.IO events — they are the data source

## Capabilities

### New Capabilities
- `live-chat-panel`: Frontend live chat panel showing danmaku messages in the right-side dialog with animated pop-in appearance, one message at a time
- `live-config-connect`: Frontend real-time room ID configuration with connect/disconnect controls in the settings panel
- `bilibili-frontend-control`: Backend Socket.IO handlers for frontend-initiated Bilibili connection control (connect, disconnect, update room ID)

### Modified Capabilities
<!-- No existing spec-level changes — the original bilibili-danmaku-integration specs (bilibili-danmaku-service, danmaku-stream-page, ai-danmaku-response) remain valid for their data and service layers, but the frontend presentation changes entirely -->

## Impact

- **Frontend** (`frontend/src/`):
  - Remove: `views/DanmakuPage.vue`, `components/chat/DanmakuStream.vue`, `components/chat/AICaptionBar.vue`
  - Modify: `components/layout/InteractivePanel.vue` (add "直播" tab), `router/index.ts` (remove `/danmaku` route), `components/layout/TitleBar.vue` (remove 弹幕 button)
  - Create: `components/chat/LiveChatPanel.vue`, `components/chat/LiveConfigPanel.vue` or integrate into existing settings
  - Update: `composables/useDanmaku.ts` (add emit methods for connect/disconnect)
  - Update: `stores/danmaku.ts` (add roomId, connection state management)

- **Backend** (`src/anima/`):
  - Modify: `orchestration/server/routes.py` — add `bilibili.connect`, `bilibili.disconnect`, `bilibili.update_room` event handlers
  - No changes to `services/live/bilibili_danmaku.py` — the service layer remains intact
