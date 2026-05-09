## Why

Current memory system stores raw conversation data and retrieves exact matches via hybrid search (Vector + BM25), but:
- **No human-like memory**: Injection format is rigid "You said / I replied" — not natural recall
- **No frontend consumption**: Chat messages are purely in-memory, no persistence, no history UI
- **No periodic learning**: Wiki has no auto-summarization; `WikiOrganizer` is manual-only
- **No meme/梗 system**: Zero infrastructure for livestream engagement or callback jokes
- **No personality evolution**: Personality is statically baked at startup, never changes based on experience

This change introduces a **three-layer memory evolution system** that transforms raw conversation data into fuzzy human-like memories, supports livestream engagement via meme management, and enables personality evolution through periodic AI learning.

## What Changes

- **New: Fuzzy Memory Layer** — Async consolidation pipeline that converts conversation turns into "I remember you said X about Y" format with configurable granularity (facts 30% / persona 20% / events 50%)
- **New: Inverted Index** — Maps fuzzy memory IDs to exact source memory IDs, enabling traceability
- **New: Hierarchical Injection Strategy** — Default: fuzzy memories only. Escalate to precise retrieval only when user persists in asking. Three tiers: Context (fuzzy summaries) → Supporting Evidence (semi-precise) → Ground Truth (exact quotes)
- **New: PeriodicLearner** — Scheduled AI-driven learning module that summarizes conversations, extracts behavioral patterns, and generates meme candidates. Runs on configurable timer.
- **New: MemePool** — 10-slot meme management system with lifecycle (generate → store → inject → score → discard/resurrect via time-decay). 80% AI-discovered + 20% user-configured.
- **New: Personality Shell** — Multi-layered personality model extending `EnhancedPersonaBuilder` (currently dead code). Core Identity + Mood State + Memory-Influenced Traits + Streaming Mode + Constraints. Runtime switchable.
- **New: Frontend Memory UI** — Memory review panel (browse fuzzy memories, view inverted index), Meme management panel (view/edit/rate memes), Personality config panel (runtime adjustment)
- **New: Scheduler Infrastructure** — `asyncio`-based periodic task system to drive PeriodicLearner and meme pool maintenance
- **Modified: MemoryMiddleware** — Injection format changed from raw "You said / I replied" to narrative fuzzy recalls. Personality-aware injection routing.
- **Modified: AgentState** — New fields for fuzzy memory context, meme injection, personality mode
- **Modified: Builder (graph)** — New nodes: `fuzzy_memory_node`, `periodic_learner_node`, `meme_inject_node`
- **Modified: PersonaConfig** — Extends with dynamic/mood/streaming personality layers

## Capabilities

### New Capabilities
- `fuzzy-memory`: Async fuzzy memory consolidation with configurable granularity, inverted index, and hierarchical injection strategy
- `periodic-learner`: Scheduled AI learning — conversation summarization, pattern extraction, meme candidate generation
- `meme-pool`: 10-slot meme lifecycle management with scoring, time-decay resurrection, and 80/20 AI/user sourcing
- `personality-shell`: Multi-layer configurable personality with runtime switching, mood states, and memory-influenced traits
- `scheduler-infra`: `asyncio`-based periodic task system for driving background processes
- `frontend-memory-ui`: Memory review, meme management, and personality configuration panels

### Modified Capabilities
- *(No existing specs to modify — first change using openspec)*

## Impact

| Area | Impact |
|------|--------|
| **New files** | ~20 files across `memory/`, `orchestration/graph/`, `frontend/src/` |
| **Modified files** | ~10 files: `memory_middleware.py`, `llm_node.py`, `builder.py`, `state.py`, `orchestrator.py`, `routes.py`, `PersonaConfig`, chat store, connection store |
| **Dependencies** | `apscheduler` or custom `asyncio` scheduler (no new heavy deps) |
| **LLM cost** | Additional calls for fuzzy consolidation and periodic learning (async, off-critical-path, configurable rate) |
| **Storage** | New SQLite tables: `fuzzy_memories`, `inverted_index`, `memes`, `learning_logs`. ~2-5MB additional for typical usage |
| **Frontend** | 3 new panels + chat store persistence (`localStorage` or `IndexedDB`) |
| **No breaking changes** | All existing functionality continues to work. New system layers on top of current memory architecture. |
