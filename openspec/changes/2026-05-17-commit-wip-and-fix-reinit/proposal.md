## Why

After the `fix-startup-bugs-parallel` OPSX change (commit `0090cf3`), Phase 2 refactoring work was started directly on the working tree without a corresponding OpenSpec change. This left 42 modified files + 67 new files uncommitted.

During server startup, `get_asgi_app()` in `socketio_server.py` is called multiple times by uvicorn (likely due to reload/fork behavior), creating duplicate `InspectionScheduler` instances. Each scheduler runs a full inspection 10s after startup — including a 30-second pipeline smoke test — and all instances fire simultaneously, causing resource exhaustion and system crash.

## What Changes

1. **Commit all current WIP** — Phase 2 refactoring (handler split, Live2D split, persistence protocol, data model extraction) plus Phase 1 inspection system improvements. This gets the working tree clean.
2. **Fix `get_asgi_app()` re-initialization** — Add a process-level guard that prevents creating duplicate resources when the function is called multiple times. Also clean up stale scheduler/warmup tasks if the function is ever re-entered.
3. **Fix type hints** — `chat_handlers.py`, `bilibili_handlers.py`, `live2d_handlers.py` still reference `AdminHandlers` in type hints but receive `BaseSocketHandler` at runtime.

## Capabilities

None — this is cleanup + stabilization, no new features.

## Impact

| Area | Change |
|------|--------|
| `src/anima/core/socketio_server.py` | Add duplicate-init guard in `get_asgi_app()` |
| `src/anima/orchestration/server/handlers/chat_handlers.py` | Type hint: `AdminHandlers` → `BaseSocketHandler` |
| `src/anima/orchestration/server/handlers/bilibili_handlers.py` | Type hint: `AdminHandlers` → `BaseSocketHandler` |
| `src/anima/orchestration/server/handlers/live2d_handlers.py` | Type hint: `AdminHandlers` → `BaseSocketHandler` |
| Working tree | Commit 42 modified + 67 new files |

No config changes. No DB migrations. No API changes.
