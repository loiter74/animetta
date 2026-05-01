## 1. Data Layer: MemoryEntry + Relations

- [x] 1.1 Create `memory_entries` and `memory_relations` SQLite DDL in `memory/storage/sqlite.py`
- [x] 1.2 Create `MemoryEntry` Pydantic model (id, memory, space_id, version, is_latest, is_static, is_forgotten, forget_after, parent_memory_id, root_memory_id, confidence, created_at, updated_at)
- [x] 1.3 Create `MemoryRelation` Pydantic model (source_id, target_id, relation type enum, created_at)
- [x] 1.4 Create `MemoryEntryStore` class encapsulating all `memory_entries` and `memory_relations` table operations (CRUD, version chain query, relation query, expire)
- [x] 1.5 Add migration: auto-create new tables on MemoryManager init if not exist
- [x] 1.6 Write unit tests for MemoryEntryStore (create, update version chain, expire, relation CRUD)

## 2. MemoryEntry Fact Extraction

- [x] 2.1 Create LLM prompt template for extracting atomic facts from conversation turns (subject-predicate-object format)
- [x] 2.2 Implement fact extraction function in `memory/`: parse conversation → list of structured MemoryEntry candidates
- [x] 2.3 Implement version matching: compare new candidate facts against existing `is_latest=1` entries to decide create-vs-update
- [x] 2.4 Integrate fact extraction into ingest flow (alongside existing WikiIngestor)
- [x] 2.5 Add `confidence` scoring based on extraction certainty signals

## 3. Memory Relations

- [x] 3.1 Create LLM prompt template for judging relationship between two MemoryEntries (updates/extends/derives/none)
- [x] 3.2 Implement relation analysis function: given new + existing entry → relation type → insert into memory_relations
- [x] 3.3 Add config flag `enable_relation_analysis` (default: true) with sampling rate setting
- [x] 3.4 Implement relation-aware search expansion: when a MemoryEntry matches, optionally fetch its related entries (via MemoryEntryStore.get_related_entries)

## 4. User Profile

- [x] 4.1 Create `UserProfile` data class with `static: List[str]` and `dynamic: List[str]`
- [x] 4.2 Implement `build_static_profile()`: extract user facts from `wiki/entities/` and `wiki/concepts/`
- [x] 4.3 Implement `build_dynamic_profile(session_id)`: summarize last N turns from ShortTermMemory
- [x] 4.4 Add `get_profile(session_id) -> UserProfile` to MemorySystem
- [x] 4.5 Integrate profile into `retrieve_context()` return value

## 5. Memory Middleware (LangGraph Integration)

- [x] 5.1 Create `MemoryMiddleware` class in `orchestration/graph/` with `before_llm_call()` and `after_llm_call()` methods
- [x] 5.2 Implement `before_llm_call()`: retrieve memories + profile → format system prompt injection block
- [x] 5.3 Implement `after_llm_call()`: build MemoryTurn → store to memory system
- [x] 5.4 Integrate middleware into `llm_node.py`: call before/after LLM invocation, integrate with existing `_retrieve_memory_context()`
- [x] 5.5 Add proper error handling: middleware failures log warning but don't block the main flow

## 6. Turn Cache

- [x] 6.1 Add `_turn_cache: dict` to MemorySystem with key = `sha256(session_id + ":" + user_input)`
- [x] 6.2 Implement cache lookup in `retrieve_context()`: return cached result if same user_input in same turn
- [x] 6.3 Implement cache invalidation: clear on new user_input (detected via session_id + turn_id change)
- [x] 6.4 Add config flag `enable_turn_cache` (default: true)

## 7. Integration & Verification

- [x] 7.1 Update MemorySystem `search()` method to optionally include MemoryEntry results alongside chunk results
- [x] 7.2 Add dedup logic in `retrieve_context()`: merge MemoryEntry + chunk results, remove duplicates
- [x] 7.3 Run full test suite to confirm no regressions in existing memory functionality (81/81 passed)
- [x] 7.4 Update docs (CLAUDE.md or memory docs) with new capabilities overview
