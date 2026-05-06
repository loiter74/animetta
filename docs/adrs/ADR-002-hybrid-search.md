# ADR-002: Chroma + SQLite FTS5 Hybrid Search

**Date:** 2026-05-01
**Status:** Accepted

## Context

Anima's memory system needs to retrieve relevant conversation history for context injection into LLM prompts. The retrieval must balance:

1. **Semantic understanding**: Find conceptually similar content even if no keywords match (e.g., "how's the weather?" should match "forecast").
2. **Keyword precision**: Find exact phrase matches when the user asks about a specific topic.
3. **Low latency**: Retrieval must complete within 100-200ms to avoid noticeable delay.
4. **Offline capability**: Must work without external API dependencies.

## Decision

Implement **hybrid search** combining:

- **70% weight**: Vector similarity search via **Chroma** (local vector database)
- **30% weight**: BM25 keyword search via **SQLite FTS5** (full-text search)

```python
final_score = 0.7 * vector_similarity + 0.3 * bm25_score
```

Key design choices:

- **Chroma** for vector storage: lightweight, embedded, no external service, supports cosine similarity.
- **SQLite FTS5** for keyword search: zero-dependency, built into Python's stdlib, fast full-text indexing.
- **Markdown as source of truth**: Each conversation is stored as a Markdown file; Chroma and SQLite are derived indexes that can be rebuilt from source.
- **Sliding-window chunking**: Conversations are chunked with overlap to preserve context boundaries.

## Consequences

**Positive:**
- Better retrieval quality than pure vector or pure keyword search (validated by recall/precision tests).
- Fully offline — no external vector DB service needed.
- Markdown-based storage is human-readable and debuggable.
- Indexes can be rebuilt from source if corrupted.

**Negative:**
- Two storage systems to maintain (Chroma + SQLite).
- Vector search quality depends on the embedding model choice.
- Chroma's in-memory mode doesn't persist across restarts by default.

## Alternatives Considered

| Alternative | Reason for Rejection |
|-------------|---------------------|
| **Pinecone** | External service, requires API key, latency over network, cost |
| **Weaviate** | Requires Docker, overkill for single-user desktop app |
| **Qdrant** | Similar to Weaviate — heavy for the use case |
| **Pure vector search** | Misses keyword-exact matches (e.g., "remember the time we talked about X") |
| **Pure keyword search** | Misses semantically similar but lexically different content |
