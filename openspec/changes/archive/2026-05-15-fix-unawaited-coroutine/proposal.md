## Why

Fix `RuntimeWarning: coroutine 'AsyncServer.emit' was never awaited` in `model_loading_manager.py:286`. The `_emit_status` helper calls `self._socketio.emit()` — an async coroutine — without `await`, causing a runtime warning on every model load/unload during startup and warmup.

## What Changes

- Modify `_emit_status` in `ModelLoadingManager` to properly schedule the coroutine using `asyncio.create_task()` or `asyncio.ensure_future()` instead of silently swallowing the unawaited coroutine
- The method signature remains synchronous — callers in both sync (`register`) and async (`_load_one`) contexts require this
- No behavioral change: Socket.IO status emission remains fire-and-forget (existing exception suppression stays)
- The `model_status` event payload schema is unchanged

## Capabilities

### New Capabilities
- `model-status-emit`: Proper async coroutine scheduling for Socket.IO model lifecycle status events during service warmup and lazy loading

### Modified Capabilities

None — this is a runtime warning fix with no spec-level behavior change.

## Impact

- **File**: `src/anima/core/model_loading_manager.py` — single method change in `_emit_status`
- **Behavior**: Identical — model status events fire at the same points with the same payload
- **Logs**: The `RuntimeWarning` on startup no longer appears
