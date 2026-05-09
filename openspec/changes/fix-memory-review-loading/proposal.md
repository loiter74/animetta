## Why

The memory review panel (记忆回顾) in the frontend is stuck on "加载记忆..." (loading) permanently and never displays fuzzy memories. The drill-down feature for memory sources also silently fails. This breaks the core memory review UX introduced in Phase 2 of the memory evolution.

## What Changes

- Fix frontend event name typo (`get_fuzzy_memeries` → `get_fuzzy_memories`) so the backend actually receives memory query requests
- Fix backend `on_get_fuzzy_memories` handler to return acknowledgment data (for Socket.IO callbacks) instead of emitting a separate event that the frontend doesn't listen for
- Fix frontend `FuzzyMemory` interface field names to match backend `FuzzyMemory.to_dict()` serialization (`text` not `content`, `last_injected_at` not `updated_at`)
- Add missing `on_get_fuzzy_memory_sources` backend handler and route registration for the drill-down feature
- Fix frontend search filter to use `text` field instead of the incorrect `content`

## Capabilities

### New Capabilities

*(None — this is a bugfix within existing capabilities)*

### Modified Capabilities

*(None — no spec-level requirement changes, only implementation-level bugfixes)*

## Impact

- **Frontend**: `frontend/src/stores/memory.ts` — event name, interface, filter logic
- **Frontend**: `frontend/src/components/memory/MemoryPanel.vue` — template field reference
- **Backend**: `src/anima/orchestration/server/routes.py` — handler return value + new sources handler + route registration
