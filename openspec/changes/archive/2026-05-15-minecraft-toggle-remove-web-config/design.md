## Context

Currently the Minecraft bot lifecycle is boot-time only: `config/tools.yaml` gates whether `init_bridge()` is called during `load_tools_from_config()`. Once started, the bridge runs until the process exits. The existing Bilibili livestream integration (`bilibili_handlers.py`) provides the exact pattern for a runtime start/stop toggle: Socket.IO events → handler → service lifecycle → status feedback.

The Web Config page (`scripts/start/web_config_server.py`) is a standalone HTTP server on port 8080 that serves a simple `config.html` from `frontend/web/`. This was a pre-Vue placeholder. All functional settings (persona, translation, Bilibili) now live in the Vue 3 frontend.

## Goals / Non-Goals

**Goals:**
- Let users start/stop the Minecraft bot from the Settings panel without editing YAML or restarting
- Show real-time bot connection status (connecting / connected / disconnected)
- Remove the dead Web Config server and its subprocess, `--no-web-config` CLI flag, and port 8080 cleanup

**Non-Goals:**
- Changing Minecraft server host/port from the UI (use `tools.yaml` for that)
- Exposing autonomous mode toggle (future work)
- Adding retry logic or graceful degradation for connection failures (existing behavior preserved)

## Decisions

**Decision 1: Follow Bilibili pattern for Minecraft toggle**

The Bilibili connect/disconnect in `bilibili_handlers.py` is the reference:
- `socket.emit('bilibili.connect', { room_id })` → `on_bilibili_connect()` → start service → emit `danmaku.status`
- `socket.emit('bilibili.disconnect')` → `on_bilibili_disconnect()` → stop service

For Minecraft:
- `socket.emit('minecraft.start')` → `on_minecraft_start()` → call `init_bridge()` + `bridge.start()` → emit `minecraft.status`
- `socket.emit('minecraft.stop')` → `on_minecraft_stop()` → call `bridge.stop()` + `cleanup_bridge()` → emit `minecraft.status`

Alternative considered: REST endpoint. Rejected — Socket.IO gives real-time status push for free and matches existing patterns.

**Decision 2: Reuse existing bridge singleton functions**

`tools/minecraft/tools.py` already has `init_bridge()` and `cleanup_bridge()`. The handler calls these directly:
- `init_bridge(config)` checks `mc_config.enabled` — need to bypass this gate and always start when the handler fires (pass a modified config dict with `enabled: True`)
- `cleanup_bridge()` calls `bridge.stop()` — already works

**Decision 3: Web Config removal is straightforward deletion**

The server has zero dependencies on other components. Remove:
- `scripts/start/web_config_server.py` (the server itself)
- `start_web_config()` from `services.py`
- `--no-web-config` flag, `start_web_config()` call, and port 8080 cleanup from `start.py`
- `frontend/web/` directory

## Risks / Trade-offs

- **[Risk]** If bridge fails to start (no Minecraft server), the UI toggle shows "connecting" indefinitely.
  → **Mitigation**: Bridge emits `minecraft.status` with `{ connected: false, error: "..." }` on failure. Store tracks error state.
- **[Risk]** Web Config page removal is **BREAKING** for anyone accessing `http://localhost:8080`.
  → **Mitigation**: The page has been superseded by the Vue 3 frontend (port 3000). No documented user flow relies on it.
