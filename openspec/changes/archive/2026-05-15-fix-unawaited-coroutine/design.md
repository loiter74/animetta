## Context

`ModelLoadingManager._emit_status()` is a synchronous helper called from both sync (`register`) and async (`_load_one`) contexts. It calls `self._socketio.emit("model_status", payload)` — a coroutine from the `python-socketio` `AsyncServer` — without `await`, producing:

```
RuntimeWarning: coroutine 'AsyncServer.emit' was never awaited
```

The emit is intentionally fire-and-forget: the existing exception handler (`try/except`) proves crashes must never propagate. The fix must preserve the sync interface while properly scheduling the coroutine.

## Goals / Non-Goals

**Goals:**
- Eliminate the `RuntimeWarning` on line 286 of `model_loading_manager.py`
- Preserve fire-and-forget semantics (Socket.IO emit is non-critical infrastructure)
- Keep `_emit_status` synchronous — both sync and async callers depend on this
- Preserve existing exception suppression and logging

**Non-Goals:**
- Refactoring `_emit_status` to be fully async (would require changing both `register()` and `_load_one()` call sites)
- Changing the `model_status` event schema or emission timing
- Adding retry logic for failed emits

## Decisions

**Decision 1: Use `asyncio.ensure_future()` over `asyncio.create_task()`**

- `ensure_future()` was chosen because it gracefully handles the case where no event loop is running (returns `None` silently), whereas `create_task()` raises `RuntimeError` in that scenario. During module-level synchronous registration, the event loop may not yet be active.
- Both correctly schedule the coroutine on the running loop, eliminating the unawaited coroutine warning.

**Decision 2: Wrap in existing try/except rather than adding new error handling**

- The current `try/except` block already catches and suppresses Socket.IO failures. Wrapping `ensure_future(emit_coro)` in the same block keeps the failure mode identical: "best effort, never crash."

## Risks / Trade-offs

- **[Low] ensure_future() returns None if no loop is running**: If `_emit_status` is called before the asyncio loop starts, the event silently drops. This is acceptable — model status events during pre-loop initialization are inherently unreliable anyway (nobody is listening yet).
- **[Low] Unawaited future reference**: The created `Task` from `ensure_future()` is intentionally fire-and-forget (no reference stored). If the task fails before being executed, the exception is silently lost — but this matches existing behavior (the exception is already caught).

## Migration Plan

Single-file, single-method change with zero behavioral impact:
1. In `_emit_status`, wrap the `self._socketio.emit()` call with `asyncio.ensure_future()`
2. No rollback needed — change is additive and behavior-preserving
