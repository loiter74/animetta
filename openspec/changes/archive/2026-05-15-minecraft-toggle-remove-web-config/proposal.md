## Why

The Minecraft bot currently has no runtime toggle — it either starts at boot (via `tools.yaml`) or never. Users need an in-app switch to start/stop the bot on demand. Additionally, the standalone Web Config page (port 8080, served from `scripts/start/web_config_server.py`) duplicates functionality already in the Vue 3 frontend settings panel and adds an unnecessary subprocess.

## What Changes

- **Add**: Minecraft start/stop toggle in `SettingsPanel.vue` (Controls tab), backed by Socket.IO events `minecraft.start` and `minecraft.stop`
- **Add**: Backend `minecraft_handlers.py` with `on_minecraft_start()` and `on_minecraft_stop()` using existing `init_bridge()`/`cleanup_bridge()`
- **Add**: `minecraftStore` Pinia store (frontend) tracking bot connection state
- **Remove**: Web Config HTTP server (`scripts/start/web_config_server.py`, `start_web_config()` in `services.py`)
- **Remove**: `frontend/web/` directory (config HTML templates)
- **Remove**: `--no-web-config` flag, `start_web_config` call, and port 8080 cleanup from `start.py`

## Capabilities

### New Capabilities
- `minecraft-toggle`: Frontend toggle + Socket.IO events to start/stop the Minecraft bot at runtime, with connection state feedback
- `web-config-removal`: Removal of the standalone Web Config HTTP server and its associated infrastructure

### Modified Capabilities
- `tool-calling`: Minecraft tools now support runtime lifecycle (start/stop) in addition to boot-time config gating

## Impact

- **Frontend**: `SettingsPanel.vue` (new toggle), `stores/minecraft.ts` (new), `types/socket-events.ts` (new events)
- **Backend**: `routes.py` (register `minecraft.start`/`minecraft.stop` events), new `handlers/minecraft_handlers.py`
- **Scripts**: `start.py` (remove `--no-web-config`, `start_web_config` call, port 8080 cleanup), `services.py` (remove `start_web_config()`)
- **Removed**: `scripts/start/web_config_server.py`, `frontend/web/`
- **No dependency changes**
