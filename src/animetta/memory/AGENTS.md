# MEMORY — V2 ATOM-BASED MEMORY SYSTEM

**Generated:** 2026-05-31
**Commit:** cdd4a87

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW

V2 atom-based memory system replacing the old wiki-architecture. Uses MemoryAtom as the fundamental unit with a lifecycle from RAW → EPISODIC → SEMANTIC → EMERGENT through CompileEngine. Hybrid search via Chroma vector DB + SQLite FTS5. LLM-driven reconsolidation for memory rewriting.

## STRUCTURE

```
memory/
├── __init__.py              # Re-exports LivingMemorySystem
└── v2/                      # V2 atom-based architecture
    ├── system.py            # LivingMemorySystem — entry point
    ├── atom.py              # MemoryAtom data model
    ├── store.py             # AtomStore — Chroma + SQLite FTS5 hybrid
    ├── search.py            # Hybrid search (Chroma vector + FTS5 keyword)
    ├── compile.py           # CompileEngine — RAW→EPISODIC→SEMANTIC→EMERGENT
    ├── metabolism.py        # MetabolismScheduler — periodic lifecycle ticks
    ├── reconsolidation.py   # ReconsolidationClient — LLM-driven memory rewrite
    └── emotion_field.py     # Emotion valence/arousal vectors
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Entry point | `v2/system.py` | `LivingMemorySystem` — all subsystems wired here |
| Add memory type | `v2/atom.py` | `MemoryAtom` model — layer, confidence, salience |
| Change search ranking | `v2/search.py` | Chroma vector + FTS5 hybrid with CJK LIKE fallback |
| Memory lifecycle | `v2/compile.py` | CompileEngine — stage-gated atom progression |
| Periodic maintenance | `v2/metabolism.py` | MetabolismScheduler — background reconsolidation ticks |
| LLM-driven rewrite | `v2/reconsolidation.py` | ReconsolidationClient — bypasses service chain (uses openai directly) |
| Vector store ops | `v2/store.py` | AtomStore — ChromaDB + SQLite FTS5, dual write |
| Emotion vectors | `v2/emotion_field.py` | Valence/arousal per atom for emotional retrieval |

## KEY PATTERNS

- **Atom lifecycle**: RAW (captured) → EPISODIC (grouped) → SEMANTIC (abstracted) → EMERGENT (insight)
- **Hybrid search**: Chroma vector + SQLite FTS5 with CJK `%query%` LIKE fallback
- **Reconsolidation**: LLM rewrites atoms during metabolism ticks, bypassing animetta service chain
- **Dual storage**: ChromaDB for vector similarity + SQLite FTS5 for keyword matching
- **Confidence + salience**: Each atom has scoring for retrieval ranking and lifecycle decisions

## ANTI-PATTERNS

- ❌ Never use pure vector or pure keyword search — always hybrid
- ❌ Never bypass CompileEngine for atom lifecycle — use `LivingMemorySystem.encode()`
- ❌ Do not add Pinecone/Weaviate/Qdrant — Chroma is locked in (ADR-002)
- ❌ Wiki / storage / learner / meme subdirectories are DELETED — do not recreate

## NOTES

- Old wiki architecture (`memory/wiki/`, `memory/storage/`, `memory/learner/`, `memory/meme/`) fully removed
- `ReconsolidationClient` uses `openai` directly, not `animetta.services.llm` — intentional bypass
- CJK FTS5 uses `%query%` LIKE fallback due to jieba tokenization limitations
- Memory integration test: `tests/integration/test_memory.py` — encode + recall through real pipeline
- Unit tests: `tests/memory_v2/` — 91 tests covering all components
- Runtime data at `memory_db/` (chroma_v2, living_memory.sqlite)
