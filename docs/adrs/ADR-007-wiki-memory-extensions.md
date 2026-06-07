# ADR-007: Wiki Memory Extensions

**Date:** 2026-06-07
**Status:** Accepted

## Context

Anima's memory system needs to go beyond simple keyword matching. The original memory system stored atoms and performed basic FTS5 search. We need emotional context, personality evolution, and meme integration.

## Decision

Extend the wiki memory system with three key components:

1. **FuzzyLayer**: 3-level injection system
   - Level 1: Direct keyword match (highest confidence)
   - Level 2: Semantic similarity via embeddings (medium confidence)
   - Level 3: Emotional congruence matching (lowest confidence, highest creativity)

2. **MemePool**: Time-decay + resurrection system
   - Memes decay in relevance over time (exponential decay)
   - Successful memes get "resurrected" when context matches
   - Pool size limited to prevent memory bloat

3. **UserProfile**: Dual-track personality model
   - Track 1: Explicit personality traits (from persona config)
   - Track 2: Implicit personality evolution (from conversation patterns)
   - Blending ratio adjustable per conversation context

## Consequences

- **Positive**: Richer, more contextual memory retrieval
- **Positive**: Personality evolves naturally over time
- **Positive**: Memes become reusable cultural artifacts
- **Negative**: Increased computational cost for memory operations
- **Negative**: More complex debugging when memory retrieval is unexpected
