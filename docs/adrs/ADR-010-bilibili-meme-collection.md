# ADR-010: Bilibili Meme Collection

**Date:** 2026-06-07
**Status:** Accepted

## Context

Anima needs to collect and analyze memes from Bilibili chat to build a meme knowledge base. The collection needs to handle high-volume chat messages and extract meaningful meme patterns.

## Decision

Implement a 3-stage meme collection pipeline:

1. **Collector**: Receives raw Bilibili chat messages via WebSocket
2. **Analyzer**: Uses LLM to identify meme candidates from chat messages
3. **Discovery**: Extracts meme patterns, stores in MemePool for reuse

### Architecture

```
Bilibili Chat → Collector → Message Queue
                           ↓
                        Analyzer → Meme Candidates
                                       ↓
                                  Discovery → MemePool
```

### Key Design Decisions

1. **Periodic collection**: Collect memes at regular intervals, not real-time (reduces load)
2. **LLM analysis**: Use LLM to understand context and identify true memes vs noise
3. **Meme patterns**: Store patterns (templates) not just instances
4. **Time-decay**: Memes lose relevance over time, preventing stale references

## Consequences

- **Positive**: Automatic meme knowledge base building
- **Positive**: Memes are context-aware and reusable
- **Positive**: Periodic collection reduces system load
- **Negative**: LLM analysis adds latency to meme availability
- **Negative**: May miss real-time trending memes
