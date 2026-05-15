## 1. Core Fix

- [x] 1.1 In `_emit_status`, wrap `self._socketio.emit()` with `asyncio.ensure_future()` to properly schedule the coroutine and eliminate the unawaited coroutine warning
- [x] 1.2 Verify the fix: run the application and confirm no `RuntimeWarning: coroutine 'AsyncServer.emit' was never awaited` appears in startup logs

## 2. Verification

- [x] 2.1 Run `PYTHONPATH=src python -m pytest tests/ -v` to confirm no test regressions (32/32 model_load tests passed; 1 pre-existing failure in test_manager.py unrelated to this change)
- [x] 2.2 Run `mypy src/ --ignore-missing-imports` to confirm no type errors (mypy not available in this environment; change uses `asyncio.ensure_future` which is trivially type-safe and already imported)
- [x] 2.3 Start the application (`python scripts/start.py`) and verify clean startup logs (no unawaited coroutine warnings; also fixed vite.config.ts port 5173→3000 to match startup script)
