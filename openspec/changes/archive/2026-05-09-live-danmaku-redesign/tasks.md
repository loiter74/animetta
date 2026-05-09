## 1. Backend — Socket.IO event handlers for frontend control

- [x] 1.1 Add `bilibili.connect` handler in `routes.py` — receives `{room_id: int}`, starts `BilibiliDanmakuService`, emits `danmaku.status`
- [x] 1.2 Add `bilibili.disconnect` handler in `routes.py` — stops `BilibiliDanmakuService`, emits `danmaku.status` with disconnected state
- [x] 1.3 Add `bilibili.update_room` handler in `routes.py` — stops current service, starts new one with updated room_id
- [x] 1.4 Register new event handlers in `register_routes()` — wire `bilibili.connect`, `bilibili.disconnect`, `bilibili.update_room` to the Socket.IO server
- [x] 1.5 Update `bilibili_config` startup logic — ensure initial auto-connect still works, but subsequent connections can be overridden by frontend

## 2. Frontend — DanmakuStore and Composable updates

- [x] 2.1 Update `stores/danmaku.ts` — add `roomId`, `isConnecting` state; add `setRoomId`, `setConnecting` actions
- [x] 2.2 Update `composables/useDanmaku.ts` — add `connect(roomId)`, `disconnect()`, `updateRoom(roomId)` emit methods; keep existing event listeners
- [x] 2.3 Update `danmaku.ai_reply` listener in `useDanmaku.ts` — forward AI replies to `useChatStore.createMessage()` as assistant messages, prefixed with "回复 @username:"

## 3. Frontend — InteractivePanel: Add "直播" tab

- [x] 3.1 Modify `InteractivePanel.vue` — add third tab button "📺 直播" alongside existing "💬 聊天" and "⚙️ 设置"
- [x] 3.2 Add `LiveChatPanel.vue` to the tab content, shown when `activeTab === 'live'`
- [x] 3.3 Add connection status indicator in the "直播" tab header (green dot = connected, red = disconnected)

## 4. Frontend — LiveChatPanel component

- [x] 4.1 Create `components/chat/LiveChatPanel.vue` — danmaku message list with pop-in CSS animation (`@keyframes popIn`: translateY(10px) → translateY(0), opacity 0 → 1, ~300ms)
- [x] 4.2 Add per-message template showing `user_name` (bold accent color) and `text` (normal text), with `:key` for proper Vue transition tracking
- [x] 4.3 Add empty state: "等待弹幕中..." with connection warning if disconnected
- [x] 4.4 Add auto-scroll behavior (watch `store.messages.length`, `nextTick()`, scroll to bottom)
- [x] 4.5 Add message count footer: "共 N 条弹幕"
- [x] 4.6 Add scrollbar styling matching existing `MessageList.vue` pattern

## 5. Frontend — Live config in Settings panel

- [x] 5.1 Add "直播设置" section to `components/settings/SettingsPanel.vue` with:
  - Room ID numeric input field (`v-model.number`)
  - "连接" button (emits `bilibili.connect`)
  - "断开" button (emits `bilibili.disconnect`)
  - Connection status display (connected/disconnected/error)
- [x] 5.2 Add loading state on connect button while `isConnecting` is true
- [x] 5.3 Add validation — room ID must be a positive integer; show error toast if invalid
- [x] 5.4 Listen for `danmaku.status` events to update connection status display in real time

## 6. Frontend — Cleanup: Remove old danmaku page and caption bar

- [x] 6.1 Delete `views/DanmakuPage.vue`
- [x] 6.2 Delete `components/chat/DanmakuStream.vue`
- [x] 6.3 Delete `components/chat/AICaptionBar.vue`
- [x] 6.4 Remove `/danmaku` route from `router/index.ts`
- [x] 6.5 Remove danmaku toggle button from `components/layout/TitleBar.vue` (the "弹幕" / "Chat" button)
