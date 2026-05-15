## 1. Backend — Minecraft Socket.IO Handler

- [x] 1.1 Create `src/anima/orchestration/server/handlers/minecraft_handlers.py` with `on_minecraft_start()` and `on_minecraft_stop()` functions, following the Bilibili handler pattern
- [x] 1.2 Register `minecraft.start` and `minecraft.stop` Socket.IO events in `routes.py`
- [x] 1.3 Emit `minecraft.status` events on connect success, connect failure, and disconnect

## 2. Frontend — Minecraft Toggle UI

- [x] 2.1 Create `frontend/src/stores/minecraft.ts` Pinia store with `connected`, `isConnecting`, `error` state
- [x] 2.2 Add `minecraft.status` listener in the store that updates state from backend events
- [x] 2.3 Add Minecraft toggle section in `SettingsPanel.vue` Controls tab, following the Bilibili connect/disconnect button pattern
- [x] 2.4 Add `minecraft.start` and `minecraft.stop` event types to `frontend/src/types/socket-events.ts`

## 3. Remove Web Config Page

- [x] 3.1 Delete `scripts/start/web_config_server.py`
- [x] 3.2 Remove `start_web_config` function from `scripts/start/services.py` and `scripts/start/__init__.py`
- [x] 3.3 Remove `--no-web-config` flag, `start_web_config()` call, and port 8080 cleanup from `scripts/start.py`
- [x] 3.4 Delete `frontend/web/` directory

## 4. Verification

- [x] 4.1 Verify backend starts without web_config import errors
- [x] 4.2 Verify `minecraft.start` and `minecraft.stop` events are registered in Socket.IO
- [x] 4.3 Verify frontend Minecraft store initializes without errors
