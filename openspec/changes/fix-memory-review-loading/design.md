## Context

The memory review panel (记忆回顾) uses Socket.IO events to fetch fuzzy memories from the backend. Three implementation-level bugs prevent it from working:

1. **Event name typo** — The frontend emits `get_fuzzy_memeries` but the backend registers `get_fuzzy_memories`. The backend never receives the request.
2. **Ack mechanism mismatch** — The frontend uses Socket.IO acknowledgment callbacks (`socket.emit(event, data, callback)`) but the backend uses `self.sio.emit('fuzzy_memories_result', ...)` (separate event) instead of returning data from the handler. The callback never fires.
3. **Field name mismatch** — Backend `FuzzyMemory.to_dict()` serializes `text` and `last_injected_at`, but the frontend interface expects `content` and `updated_at`.
4. **Missing handler** — The drill-down feature emits `get_fuzzy_memory_sources` but there is no backend handler registered.

All four are pure implementation bugs — the spec-level requirements and data model are correct.

## Goals / Non-Goals

**Goals:**
- Fix the memory review panel so it displays fuzzy memories on load
- Fix the drill-down feature so it shows memory sources
- Keep all changes minimal — no refactoring, no new capabilities

**Non-Goals:**
- No changes to the backend data model or serialization format
- No new API endpoints or Socket.IO events
- No changes to fuzzy memory storage or consolidation logic

## Decisions

1. **Use handler return values instead of emit** — python-socketio async handlers automatically send return values as acknowledgments to the client's callback. This is simpler and more correct than emitting a separate event that the frontend would need to listen for.
2. **Fix frontend interface to match backend** — The backend `to_dict()` is the API contract. Changed the frontend `FuzzyMemory` interface to use `text` and `last_injected_at` (matching the backend) rather than changing the backend to emit `content` and `updated_at`.
3. **Add the missing sources handler** — Follows the exact same pattern as `on_get_fuzzy_memories` and reuses the existing `FuzzyMemoryStore.get_sources()` method.

## Risks / Trade-offs

- **[Low] Clients with stale frontend builds** — Since the fix is in both frontend and backend, both need to be deployed. The error was silent (loading spinner never resolves), so no crash on stale clients.
- **[Low] TypeScript interface widening** — The updated `FuzzyMemory` interface includes all backend fields (`session_id`, `source_turn_ids`, `last_injected_at`, `injection_count`). This makes the interface more accurate but exposes fields the template doesn't use. No practical risk.
