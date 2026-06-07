# ADR-009: Live2D Expression System

**Date:** 2026-06-07
**Status:** Accepted

## Context

Anima's Live2D avatar needs to express emotions naturally. The original system used hardcoded mappings from emotion labels to expression parameters. This was inflexible and didn't account for context.

## Decision

Implement a multi-stage emotion analysis pipeline:

1. **Keyword Analysis**: Fast, rule-based emotion detection from text
2. **LLM Analysis**: Deep emotion understanding using the conversation LLM
3. **Mapper**: Converts emotion analysis results to Live2D parameters
4. **Strategy**: Blends multiple emotion sources, handles transitions

### Pipeline

```
Text → Keyword Analysis → Emotion Labels
     → LLM Analysis    → Emotion Labels
                       ↓
                    Mapper → Live2D Parameters
                       ↑
                    Strategy → Blended Emotion
```

### Key Design Decisions

1. **Separation of concerns**: Analyzer, mapper, and strategy are independent components
2. **Multiple analyzers**: Keyword (fast) + LLM (accurate) provide complementary analysis
3. **Smooth transitions**: Strategy handles emotion blending to avoid jarring expression changes
4. **Configurable**: Each stage can be tuned independently

## Consequences

- **Positive**: Natural, context-aware expressions
- **Positive**: Easy to add new emotion analyzers
- **Positive**: Smooth expression transitions
- **Negative**: LLM analysis adds latency
- **Negative**: More complex than hardcoded mappings
