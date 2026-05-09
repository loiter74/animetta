# MEMORY — WIKI-ARCHITECTURE MEMORY SYSTEM

**Generated:** 2026-05-10

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW

Hybrid memory system combining Chroma vector DB, SQLite FTS5 keyword search, and Markdown-based wiki storage. Second most complex domain after orchestration.

## STRUCTURE

```
memory/
├── system.py               # MemorySystem entry point — 373 lines
├── config.py               # Memory configuration
├── fact_extractor.py       # Fact extraction from conversations — 384 lines
├── prompts.py              # LLM prompts for memory ops
├── user_profile.py         # User profile model + builder
├── manager.py              # Legacy compat wrapper (`# ── legacy compat ──`)
├── tools.py                # Memory tools for LLM
├── search/                 # Hybrid search engine
│   ├── hybrid.py           # 70% vector + 30% BM25 fusion
│   └── scorer.py           # Relevance scoring
├── storage/                # Persistence layer
│   ├── chroma.py           # Chroma vector store
│   ├── sqlite.py           # SQLite FTS5 keyword index
│   └── memory_entry_store.py  # Memory entry CRUD + version chain
├── wiki/                   # Markdown knowledge base
│   ├── manager.py          # Wiki manager entry point
│   ├── organizer.py        # Wiki organization — 442 lines (HOT)
│   ├── ingestor.py         # Conversation → markdown ingestion
│   ├── parser.py           # Markdown parsing
│   └── sources/            # Source integration
├── learner/                # Pattern extraction + learning
│   ├── engine.py           # Learning engine — 408 lines
│   └── pattern_extractor.py  # Pattern extraction — 414 lines
├── meme/                   # Meme system
├── fuzzy/                  # Fuzzy memory layer
├── models/                 # Pydantic data models
│   └── base.py             # MemoryEntry, MemoryFragment, etc.
└── stores/                 # Additional stores
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Entry point | `system.py` | `MemorySystem` class — all subsystems wired here |
| Add memory type | `models/base.py` | Define new Pydantic model |
| Change search ranking | `search/hybrid.py` | 70/30 vector/BM25 blend |
| Change wiki behavior | `wiki/organizer.py` | 442 lines — largest memory file |
| Add learning pattern | `learner/pattern_extractor.py` | 414 lines |
| Fact extraction | `fact_extractor.py` | LLM-driven fact extraction |
| Vector store ops | `storage/chroma.py` | ChromaDB client |

## KEY PATTERNS

- **Wiki architecture** (ADR-005): Markdown files are source of truth, Chroma + SQLite for search
- **Hybrid search**: 70% vector similarity + 30% BM25 keyword (ADR-002)
- **Version chain**: `MemoryEntryStore` maintains entry version history
- **Legacy compat**: `manager.py:192` has a `# ── legacy compat ──` wrapper — do not remove without migration

## ANTI-PATTERNS

- ❌ Never use pure vector or pure keyword search — always hybrid
- ❌ Never bypass Markdown as source of truth
- ❌ Do not add Pinecone/Weaviate/Qdrant — Chroma is locked in (ADR-002)

## NOTES

- `wiki/organizer.py` (442 lines) + `wiki/ingestor.py` are the wiki hotspots — consider splitting query from mutation logic.
- `learner/pattern_extractor.py` (414) + `engine.py` (408) form a major sub-system.
- `self.fuzzy` in `system.py:67` is a backward compat alias — do not break it.
- Legacy compat exists in `manager.py:192` — deprecation planned but not yet executed.
