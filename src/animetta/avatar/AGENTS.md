# AVATAR — EMOTION ANALYSIS & LIVE2D MAPPING

**Generated:** 2026-05-23
**Commit:** 8930c5f

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW
Emotion extraction pipeline: LLM response text → emotion analysis (keyword/LLM/audio) → Live2D parameter mapping → expression strategy (duration/intensity/position). Bridges the gap between LLM output and Live2D avatar behavior.

## STRUCTURE
```
avatar/
├── analyzers/               # Emotion extraction
│   ├── base.py              #   Abstract emotion analyzer
│   ├── keyword.py           #   Keyword-based emotion detection
│   ├── llm_tag.py           #   LLM-tagged emotion extraction
│   └── audio.py             #   Audio-based emotion detection
├── mappers/                 # Emotion → Live2D parameter mapping
│   ├── base.py              #   Base mapper interface
│   ├── emotion_param_mapper.py  # Main mapping implementation
│   └── config/              #   emotion_mappings.yaml — rules
├── strategies/              # Expression application strategies
│   ├── base.py              #   Abstract strategy
│   ├── duration.py          #   How long expressions last
│   ├── intensity.py         #   Expression intensity levels
│   └── position.py          #   When to apply expressions
├── factory.py               # EmotionAnalyzerFactory — builds pipeline
└── prompts.py               # LLM prompts for emotion tagging
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add emotion detection | `analyzers/` | Subclass base.py, register in factory.py |
| Change emotion mapping | `mappers/config/emotion_mappings.yaml` | YAML: emotion → Live2D params |
| Change expression timing | `strategies/duration.py` | Default duration, overlap rules |
| LLM emotion prompts | `prompts.py` | System prompts for LLM tagging |
| Pipeline assembly | `factory.py` | Wires analyzers → mappers → strategies |

## KEY PATTERNS
- **Analyzer → Mapper → Strategy pipeline**: text → emotion label → Live2D params → expression
- **Factory pattern**: EmotionAnalyzerFactory assembles analyzers from config
- **YAML-driven mapping**: emotion_mappings.yaml defines param rules

## ANTI-PATTERNS
- Never hardcode emotion mappings in Python — use emotion_mappings.yaml
- Never bypass the factory — all analyzers must flow through factory.py
- Do not add emotion logic to graph nodes — delegate to analyzers here

## NOTES
- Frontend Live2D rendering is in `frontend/src/components/live2d/` — this package handles analysis only
- Emotion mappings flow: LLM response → analyzers → mappers → strategies → services/live2d/ action queue
