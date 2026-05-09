## 1. Backend: Fix event handler ack + add missing sources handler

- [x] 1.1 Change `on_get_fuzzy_memories` return type from `None` to `dict` — return data instead of emitting `fuzzy_memories_result` event
- [x] 1.2 Add `on_get_fuzzy_memory_sources` handler that queries `FuzzyMemoryStore.get_sources()` and returns source entries
- [x] 1.3 Register `get_fuzzy_memory_sources` route in `register_routes()`

## 2. Frontend: Fix event name, interface, and template

- [x] 2.1 Fix event name typo in `memory.ts`: `get_fuzzy_memeries` → `get_fuzzy_memories`
- [x] 2.2 Fix `FuzzyMemory` interface to match backend `to_dict()`: `content` → `text`, `updated_at` → `last_injected_at`, add missing backend fields
- [x] 2.3 Fix search filter in `memory.ts`: `m.content` → `m.text`
- [x] 2.4 Fix template in `MemoryPanel.vue`: `item.content` → `item.text`

## 3. Verify

- [x] 3.1 Frontend TypeScript compiles clean (`vue-tsc --noEmit --skipLibCheck`)
- [x] 3.2 Backend Python parses clean (`ast.parse()`)
- [x] 3.3 All MemePool tests pass (related backend module)
