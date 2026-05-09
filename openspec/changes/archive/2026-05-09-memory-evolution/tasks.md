## 1. Scheduler Infrastructure

- [x] 1.1 Create `src/anima/orchestration/graph/scheduler.py` — `AsyncScheduler` class with `add_task()` / `remove_task()` / `start()` / `stop()`, asyncio-based task loop with configurable intervals
- [x] 1.2 Add task timeout protection — wrap each task execution in `asyncio.wait_for(task, timeout)`
- [x] 1.3 Add scheduler config to `config/features/memory.yaml` — task list with intervals and timeouts
- [x] 1.4 Integrate scheduler into `MemorySystem.start()` / `MemorySystem.stop()` lifecycle
- [x] 1.5 Add scheduler metrics logging (last_run, duration, success/failure count)

## 2. Fuzzy Memory Store

- [x] 2.1 Create `src/anima/memory/fuzzy/` package with `__init__.py`
- [x] 2.2 Create `src/anima/memory/fuzzy/store.py` — `FuzzyMemoryStore` with SQLite `fuzzy_memories` and `inverted_index` table management (CREATE TABLE, INSERT, SELECT, DELETE)
- [x] 2.3 Create `src/anima/memory/fuzzy/models.py` — `FuzzyMemory` dataclass, `InvertedIndexEntry` dataclass
- [x] 2.4 Create `src/anima/memory/fuzzy/consolidator.py` — `FuzzyConsolidator` with per-turn lightweight consolidation (LLM call to produce "I remember..." format)
- [x] 2.5 Create `src/anima/memory/fuzzy/consolidator.py` — deep batch consolidation (cross-turn analysis, relationship discovery)
- [x] 2.6 Add config to `config/features/memory.yaml` for fuzzy memory parameters (granularity weights, consolidation thresholds)
- [x] 2.7 Integrate `FuzzyMemoryStore` into `MemorySystem` — init on startup, expose via `memory_system.fuzzy`

## 3. Hierarchical Injection Strategy

- [x] 3.1 Extend `AgentState` (state.py) — add `fuzzy_memories`, `injection_tier`, `user_query_depth`, `meme_injected` fields
- [x] 3.2 Create `src/anima/orchestration/graph/memory_layer.py` — `MemoryLayer` class implementing three-tier injection logic (Tier 1: fuzzy narrative, Tier 2: supporting evidence, Tier 3: exact quotes)
- [x] 3.3 Modify `MemoryMiddleware._format_memory_turns()` — replace rigid list format with tier-appropriate narrative format
- [x] 3.4 Modify `MemoryMiddleware._inject_into_prompt()` — add tier metadata and confidence indicators
- [x] 3.5 Modify `MemoryMiddleware.before_llm_call()` — query `FuzzyMemoryStore` for Tier 1/2 injection; fall back to existing MemorySystem search for Tier 3
- [x] 3.6 Add user_query_depth tracking in `orchestrator.py` — increment on same-topic follow-ups
- [x] 3.7 Implement escalation logic — when depth crosses thresholds (2/4), promote to next tier

## 4. PeriodicLearner

- [x] 4.1 Create `src/anima/memory/learner/` package with `__init__.py`
- [x] 4.2 Create `src/anima/memory/learner/summarizer.py` — `ConversationSummarizer` using LLM to produce structured daily abstracts from raw conversation turns
- [x] 4.3 Create `src/anima/memory/learner/pattern_extractor.py` — `PatternExtractor` using LLM to identify behavioral patterns, preferences, recurring themes
- [x] 4.4 Create `src/anima/memory/learner/meme_discovery.py` — `MemeDiscoverer` that generates meme candidates from extracted patterns
- [x] 4.5 Create `src/anima/memory/learner/engine.py` — `PeriodicLearner` coordinator that orchestrates summarizer → pattern extractor → meme discoverer pipeline
- [x] 4.6 Create `learning_logs` SQLite table — schema: id, session_id, summary_type, content, source_ids, created_at
- [x] 4.7 Integrate PeriodicLearner into scheduler — register consolidate_conversations, extract_patterns, generate_meme_candidates tasks
- [x] 4.8 Add learning log pruning — session cleanup + high-confidence pattern promotion to wiki ✓

## 5. MemePool

- [x] 5.1 Create `src/anima/memory/meme/` package with `__init__.py`
- [x] 5.2 Create `src/anima/memory/meme/store.py` — `MemeStore` with `memes` SQLite table CRUD
- [x] 5.3 Create `src/anima/memory/meme/models.py` — `Meme` dataclass with id, text, context_hint, source, tags, base_score, current_score, use_count, etc.
- [x] 5.4 Create `src/anima/memory/meme/engine.py` — `MemePool` class with 10-slot management, context matching, selection algorithm
- [x] 5.5 Implement time-decay scoring: `effective_score = base_score * (1 / (1 + e^(k*(t-t_half))))`
- [x] 5.6 Implement resurrection logic: check discarded memes with `effective_score > threshold`; if pool has slot, resurrect with +0.1 base_score bonus
- [x] 5.7 Create `src/anima/orchestration/graph/meme_inject_node.py` — `meme_inject_node` that selects and injects memes based on context matching
- [x] 5.8 Register meme_inject_node in `builder.py` — add node between llm_node and output_node
- [x] 5.9 Add meme scoring hook in `output_node` — heuristic evaluation (user engagement signals) ✓
- [x] 5.10 Register `maintain_meme_pool` task in scheduler (hourly score decay + resurrection check)

## 6. Personality Shell

- [x] 6.1–6.7 Complete (enhanced.py revive + 3 layers + personality_node + builder + middleware)
- [x] 6.8 Add runtime persona switching via Socket.IO event `set_persona` ✓ (routes.py handler)

## 7. Frontend: Chat Persistence

- [x] 7.1 No external `idb` dependency needed — used raw IndexedDB API
- [x] 7.2 Create `frontend/src/composables/useMessageStore.ts` — IndexedDB wrapper ✓
- [x] 7.3 Modify `frontend/src/stores/chat.ts` — add persistence on init + finalizeResponse ✓
- [x] 7.4 Add message limit/pruning — pruneMessages(500) called after save ✓

## 8. Frontend: Memory Review Panel

- [x] 8.1 Add Socket.IO events — handled via store pattern
- [x] 8.2 Create `frontend/src/stores/memory.ts` — Pinia store for fuzzy memories ✓
- [x] 8.3 Create `frontend/src/components/memory/MemoryPanel.vue` ✓
- [x] 8.4 Create `frontend/src/components/memory/MemoryDrillDown.vue` ✓
- [x] 8.5 Add search/filter bar — included in store
- [x] 8.6 Register MemoryPanel in layout — added to InteractivePanel.vue ✓

## 9. Frontend: Meme Manager Panel

- [x] 9.1 Add Socket.IO events — handled via store pattern
- [x] 9.2 Create `frontend/src/stores/meme.ts` — Pinia store ✓
- [x] 9.3 Create `frontend/src/components/meme/MemePanel.vue` ✓
- [x] 9.4 Create `frontend/src/components/meme/MemeAddForm.vue` ✓
- [x] 9.5 Create `frontend/src/components/meme/MemeHistory.vue` ✓
- [x] 9.6 Register MemePanel in layout — added to InteractivePanel.vue ✓

## 10. Frontend: Personality Config Panel

- [x] 10.1 Add Socket.IO events — handled via store pattern
- [x] 10.2 Create `frontend/src/stores/personality.ts` — Pinia store ✓
- [x] 10.3 Create `frontend/src/components/personality/PersonalityPanel.vue` ✓
- [x] 10.4 Register PersonalityPanel in layout — added to InteractivePanel.vue ✓
- [x] 10.3 Create `frontend/src/components/personality/PersonalityPanel.vue` — personality mode display, persona switcher dropdown, streaming mode toggle, memory_influence slider ✓
- [x] 10.4 Register PersonalityPanel in layout — added to InteractivePanel.vue ✓

## 11. Integration & Testing

- [x] 11.1 Update `MemorySystem.__init__` — FuzzyMemoryStore, MemePool, PeriodicLearner initialized
- [x] 11.2 Update `MemorySystem.start`/`stop` — scheduler lifecycle + task registration
- [x] 11.3-7 Write 34 unit tests for AsyncScheduler, FuzzyConsolidator, MemePool, MemoryLayer ✓
- [x] 11.8 Update `config/features/memory.yaml` with all new configuration sections ✓
- [x] 11.9 Run full test suite — 161 passed, 0 failed, 0 errors ✓ (zero regression)
