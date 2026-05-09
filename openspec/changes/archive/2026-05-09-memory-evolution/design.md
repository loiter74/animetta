## Context

The current Anima memory system has three functional layers (ShortTermMemory → Wiki Architecture → SQLite+Chroma storage) and a `MemoryMiddleware` that injects raw "You said / I replied" formatted memories into the LLM prompt. However, it lacks:

- **Human-like recall**: Memories are injected as structured logs, not as narrative fuzzy recall
- **Periodic learning**: No scheduled AI summarization — `WikiOrganizer` only runs manually
- **Meme/engagement system**: No infrastructure for livestream callback jokes
- **Dynamic personality**: `EnhancedPersonaBuilder` (296 lines) is dead code; personality never changes at runtime
- **Frontend memory UX**: Chat messages are purely in-memory, lost on page refresh

This design introduces six new capabilities that layer on top of the existing architecture without breaking any current functionality.

## Architecture Overview

```
                         ┌─────────────────────────────────────┐
                         │         Frontend (Vue 3)             │
                         │  ┌─────────┐ ┌──────┐ ┌──────────┐  │
                         │  │ Memory  │ │Meme  │ │Personality│  │
                         │  │ Panel   │ │Panel │ │ Panel     │  │
                         │  └────┬────┘ └──┬───┘ └─────┬────┘  │
                         └───────┼─────────┼───────────┼───────┘
                                 │ Socket  │ Socket    │ Socket
                                 ▼         ▼           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      LangGraph Orchestrator                      │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────┐ │
│  │llm_node  │  │meme_inject   │  │personality│  │output_node │ │
│  │(RAG+注入)│←─│_node (直播)  │←─│_node(动调)│  │(存储)      │ │
│  └────┬─────┘  └──────┬───────┘  └─────┬─────┘  └─────┬──────┘ │
│       │               │                │               │        │
│       └───────┬───────┴────────────────┘               │        │
│               │                                        │        │
│        ┌──────▼──────┐                         ┌───────▼─────┐ │
│        │MemoryLayer  │                         │   Storage   │ │
│        │(模糊/精确分层)│                         └───────┬─────┘ │
│        └──────┬──────┘                                 │        │
└───────────────┼─────────────────────────────────────────┼────────┘
                │                                         │
                ▼                                         ▼
     ┌──────────────────────┐              ┌──────────────────────┐
     │   Fuzzy Memory Store │              │  Existing Memory     │
     │   (SQLite new tables)│              │  SQLite+Chroma+Wiki  │
     │   ┌────────────────┐ │              └──────────────────────┘
     │   │ fuzzy_memories │ │                         ▲
     │   │ inverted_index │ │                         │
     │   │ memes          │ │    ┌────────────────────┘
     │   │ learning_logs  │ │    │
     │   └────────────────┘ │    │
     └──────────────────────┘    │
                │                │
          ┌─────▼────────────────▼─────┐
          │   PeriodicLearner           │
          │   (scheduled by Scheduler)  │
          │   ① 对话总结                 │
          │   ② 模式提取 → 梗候选       │
          │   ③ Wiki 自动 synthesis     │
          └────────────────────────────┘
```

## Goals / Non-Goals

**Goals:**
- Add fuzzy memory consolidation pipeline (async, non-blocking)
- Add inverted index linking fuzzy → exact memories
- Add hierarchical injection (fuzzy default, escalate on user persistence)
- Add periodic AI learning module (summarization + pattern extraction)
- Add 10-slot meme pool with lifecycle management (80% AI + 20% user)
- Add multi-layer personality shell (revive `EnhancedPersonaBuilder`)
- Add frontend panels for memory/meme/personality management
- Add scheduler infrastructure for periodic tasks
- Zero regression on existing conversation flow

**Non-Goals:**
- Not replacing the existing wiki/memory architecture (fuzzy layer sits on top)
- Not adding real-time token-by-token streaming to frontend (out of scope for this change)
- Not adding multi-modal memory (images/audio recall)
- Not implementing full RPG personality system (personality shell is configurable, not emergent)

## Decisions

### D1: Fuzzy Memory Consolidation — Async Event-Driven + Batch

**Decision**: Hybrid approach — trigger lightweight consolidation after each conversation turn (via `asyncio.create_task`), AND run deep batch consolidation on a timer.

**Rationale**:
- Per-turn: Captures immediate context, low latency impact (runs in background)
- Batch: Does cross-turn pattern analysis, relationship discovery, meme candidate generation
- Reuses existing `asyncio.create_task` pattern from `WikiIngestor.ingest_turn()`

**Alternatives considered**:
- Only batch: Misses immediate context, memories feel stale
- Only per-turn: Misses cross-session patterns, expensive (N LLM calls per N turns)

### D2: Injection Strategy — Hierarchical Three-Tier

**Decision**: Three-tier injection with escalation on user persistence.

```
Tier 1 — Context (default): "我记得用户说过喜欢编程..."
Tier 2 — Supporting (user asks "具体说说?"): "用户提过他用 TypeScript，偏好函数式风格"
Tier 3 — Ground Truth (user insists "你确定吗?"): Exact quote + source reference
```

**Implementation**: Track `user_query_depth` counter in `AgentState.metadata`. Each follow-up question in same session increments. Thresholds: Tier 1 → Tier 2 at depth ≥ 2, Tier 3 at depth ≥ 4.

### D3: Meme Pool Scoring & Resurrection

**Decision**: Logistic decay + threshold-based resurrection.

```python
effective_score = base_score * (1 / (1 + e^(k * (t - t_half))))
# k = decay rate, t_half = half-life in days
# If effective_score > resurrection_threshold AND pool has slot → resurrect
```

Default: `k = 0.5`, `t_half = 7 days`, `resurrection_threshold = 0.6`

When a meme is resurrected, it gets a bonus `+0.1` to `base_score` (so good memes get stronger over time).

### D4: Scheduler — Custom asyncio, Not APScheduler

**Decision**: Build lightweight `asyncio`-based scheduler instead of adding APScheduler dependency.

**Rationale**:
- Only need 2-3 periodic tasks (PeriodicLearner, meme pool maintenance, optional wiki upkeep)
- Existing codebase has zero scheduler deps — adding APScheduler is overkill
- Pattern: `asyncio.Task` with `while True: await asyncio.sleep(interval); await task()`
- Configurable intervals via `config/features/memory.yaml`

### D5: Personality Shell — Revive EnhancedPersonaBuilder

**Decision**: Revive `config/persona/enhanced.py` (296 lines of dead code) as the base, extend with mood/streaming layers.

The existing `EnhancedPersonaBuilder` already has: `emotion_rules`, `expertise`, `interaction_rules`, `response_templates`, `restrictions`, `user_context`. Add:

- `mood_states`: happy/sad/angry/surprised/thinking/neutral with per-state prompt overrides
- `streaming_mode`: separate personality behavior when processing danmaku (shorter replies, more memes)
- `memory_influence_weight`: how much memory shapes personality (0.0 = static, 1.0 = fully memory-driven)

### D6: Frontend Storage — IndexedDB via idb library

**Decision**: Use IndexedDB (via `idb` wrapper, already compatible with Vue 3) for chat message persistence.

**Rationale**:
- `localStorage` 5MB limit insufficient for long conversations
- `IndexedDB` async, large storage, structured queries
- `idb` library is 2KB, zero dependencies
- Pinia persist plugin alternative considered but adds coupling to specific storage backend

### D7: Meme Source Split — 80% AI / 20% User

**Decision**:
- **AI-discovered (80%)**: PeriodicLearner extracts patterns from wiki synthesis, conversation topics, repeated interactions. Config `tools.yaml` meme_enabled_tools: `[web_search]` allows external meme discovery.
- **User-configured (20%)**: Frontend Meme Panel has "Add Meme" form — text, context hint, tags. Stored in `memes` table with `source='user'`.

## Data Model

### New SQLite Tables

```sql
-- Fuzzy memories (consolidated recall)
CREATE TABLE fuzzy_memories (
    id TEXT PRIMARY KEY,                      -- 'fuzzy_{uuid4_short}'
    session_id TEXT NOT NULL,
    text TEXT NOT NULL,                        -- "我记得用户说过..."
    granularity TEXT NOT NULL,                 -- 'fact' | 'persona' | 'event'
    confidence REAL DEFAULT 0.7,               -- LLM confidence score
    source_turn_ids TEXT NOT NULL,              -- JSON array of source MemoryTurn IDs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_injected_at TIMESTAMP,                -- last time used in LLM context
    injection_count INTEGER DEFAULT 0
);

-- Inverted index: fuzzy → exact
CREATE TABLE inverted_index (
    fuzzy_id TEXT NOT NULL REFERENCES fuzzy_memories(id),
    exact_type TEXT NOT NULL,                  -- 'memory_turn' | 'memory_entry' | 'wiki_page'
    exact_id TEXT NOT NULL,                    -- the exact record identifier
    relevance REAL DEFAULT 1.0,                -- how relevant this exact memory is
    PRIMARY KEY (fuzzy_id, exact_type, exact_id)
);

-- Meme pool
CREATE TABLE memes (
    id TEXT PRIMARY KEY,                       -- 'meme_{uuid4_short}'
    text TEXT NOT NULL,                        -- 梗文本
    context_hint TEXT,                         -- 适合使用的上下文描述
    source TEXT NOT NULL DEFAULT 'ai',          -- 'ai' | 'user'
    tags TEXT DEFAULT '[]',                     -- JSON array of tags
    base_score REAL DEFAULT 0.7,
    current_score REAL DEFAULT 0.7,
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    resurrection_count INTEGER DEFAULT 0
);

-- Learning logs (PeriodicLearner output)
CREATE TABLE learning_logs (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    summary_type TEXT NOT NULL,                -- 'conversation' | 'pattern' | 'meme_candidate'
    content TEXT NOT NULL,
    source_ids TEXT,                           -- JSON array of source references
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### AgentState Extensions

```python
# New fields in AgentState (state.py)
{
    "fuzzy_memories": [],           # Injected fuzzy memory strings (Tier 1/2)
    "injection_tier": 1,            # Current injection tier (1=context, 2=supporting, 3=ground_truth)
    "user_query_depth": 0,          # Number of follow-up questions in current exchange
    "meme_candidates": [],          # Memes selected for potential injection this turn
    "meme_injected": False,         # Whether a meme was injected this turn
    "personality_mode": "default",  # 'default' | 'streaming' | 'mood_xxx'
    "personality_mood": None,       # Current mood override
}
```

## Integration Points

### Graph Changes

```
[START] → route_input()
    │
    ├── audio → [asr_node]
    │
    └── text ─────────────────────────────────────────┐
                                                      │
    ┌─────────────────────────────────────────────────▼┐
    │  [personality_node] NEW                          │
    │  · Determine current personality mode/mood       │
    │  · Load dynamic traits from memory               │
    │  · Build personality overlay prompt              │
    └─────────────────────┬───────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────┐
    │  [llm_node] MODIFIED                            │
    │  · Tiered injection (fuzzy → supporting → exact)│
    │  · Meme injection (if streaming mode)           │
    │  · Personality overlay merged into system_prompt │
    └─────────────────────┬───────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────┐
    │  [output_node] MODIFIED                         │
    │  · Store turn (existing)                        │
    │  · Trigger async fuzzy consolidation (NEW)      │
    │  · Score used meme (NEW)                        │
    └─────────────────────────────────────────────────┘
```

### MemoryMiddleware Changes

The current `_format_memory_turns()` produces:
```
## Related Memories
1. You said: [text]
   I replied: [text]
```

New behavior:
- **Tier 1** (default): Inject `fuzzy_memories` in narrative format
- **Tier 2** (depth ≥2): Inject semi-precise summaries with source confidence
- **Tier 3** (depth ≥4): Inject exact quotes + wiki page references

### PeriodicLearner Schedule

| Task | Interval | Description |
|------|----------|-------------|
| `consolidate_conversations` | Every 10 turns or 1h | Run LLM summarization on recent unconsolidated turns |
| `extract_patterns` | Every 24h | Cross-session pattern analysis → wiki synthesis |
| `generate_meme_candidates` | Every 6h | Extract meme-able patterns → MemePool candidates |
| `maintain_meme_pool` | Every 1h | Score decay, resurrection check, trim to 10 active |

All intervals configurable in `config/features/memory.yaml`.

## Risks / Trade-offs

| Risk | Severity | Mitigation |
|------|----------|------------|
| LLM cost for fuzzy consolidation | Medium | Configurable rate; async off-critical-path; tiered (per-turn lightweight + batch deep) |
| Fuzzy memory inaccuracy | Medium | Inverted index guarantees traceability; confidence scores; user can drill to exact |
| Meme inappropriateness | Medium | Context matching before injection; user can delete/re-rate; scoring filter |
| Scheduler task pileup | Low | Single-threaded asyncio scheduler; task timeout; configurable intervals |
| Frontend IndexedDB migration | Low | Chat store persists on write; graceful degradation if IndexedDB unavailable |
| Personality layer conflicts | Medium | Priority matrix: explicit user config > memory-influenced > mood > default |

## Migration Plan

The system is designed to be deployed incrementally with zero downtime:

1. **Phase 1** (backend infra): Scheduler + FuzzyMemory store + PeriodicLearner — adds tables, no behavioral change
2. **Phase 2** (injection): Modify MemoryMiddleware for tiered injection — fuzzy becomes default, exact becomes fallback
3. **Phase 3** (meme): MemePool + meme_inject_node + integration with Bilibili danmaku pipeline
4. **Phase 4** (personality): Revive EnhancedPersonaBuilder + personality_node + runtime switching
5. **Phase 5** (frontend): Memory/Meme/Personality panels + IndexedDB persistence

**Rollback**: Each phase is independently revertible. Phase 1 has zero user-facing impact. Phase 2 can be reverted by restoring original MemoryMiddleware `_format_memory_turns()`.

## Open Questions

1. Should meme injection be a dedicated graph node or a tool call? (Decision: Node for automatic injection, Tool for explicit user request)
2. Personality mood detection — from emotion_node output or separate analysis? (Proposal: from emotion_node, with memory influence weighting)
3. Frontend memory panel — embed in sidebar or separate window? (Proposal: collapsible sidebar panel, same pattern as subtitle config)
