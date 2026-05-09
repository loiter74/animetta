# ANIMA BACKEND — PYTHON PACKAGE

**Generated:** 2026-05-10
**Commit:** ff90d6d

> Parent: [../AGENTS.md](../AGENTS.md) — root project conventions and anti-patterns.

## OVERVIEW
Python backend for Anima VTuber — FastAPI + LangGraph + Socket.IO orchestration with plugin-based provider architecture. 202 files, 30.4K lines, max depth 3.

## STRUCTURE
```
src/anima/
├── core/                    # Entry point + service container (5 files)
├── orchestration/           # → see orchestration/AGENTS.md
│   ├── graph/               # LangGraph nodes + orchestrator (19 files)
│   └── server/              # WebSocket routes + sessions (8 files)
├── services/                # → see services/AGENTS.md
│   ├── speech/{asr,tts}/    # Speech recognition + synthesis
│   ├── intelligence/{llm,vad}/  # Language models + voice activity
│   ├── audio/               # Audio processing pipeline
│   └── live2d/              # Live2D action queue + viseme sync
├── memory/                  # → see memory/AGENTS.md
│   ├── wiki/                # Markdown-based knowledge storage
│   ├── search/              # Hybrid search (70% vector + 30% BM25)
│   ├── storage/             # Chroma + SQLite stores
│   ├── learner/             # Pattern extraction + learning
│   └── meme/                # Meme system
├── config/                  # Pydantic configs (YAML-driven)
│   ├── providers/{llm,asr,tts,vad}/  # Provider config classes
│   ├── persona/             # Character personality configs
│   └── core/registry.py     # @ProviderRegistry decorator
├── avatar/                  # Live2D emotion/expression analysis
│   ├── analyzers/           # Keyword + LLM-based emotion extraction
│   ├── mappers/             # Emotion → Live2D parameter mapping
│   └── strategies/          # Duration/intensity/position strategies
├── tools/                   # Tool calling + MCP bridge
├── tracing/                 # OpenTelemetry observability
└── utils/                   # Helpers
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Main server entry | `core/socketio_server.py` | FastAPI + Socket.IO ASGI app |
| Service lifecycle | `core/service_pool.py` | Shared engines (LLM/TTS/ASR), per-session VAD/memory |
| Model loading | `core/model_loading_manager.py` | Loads all models, don't block on failures |
| Provider registration | `config/core/registry.py` | `@ProviderRegistry.register_service` decorator |
| App config | `config/app.py` | 433 lines — main config schema |
| Graph node template | `orchestration/graph/__init__.py` | Node docstring explains pattern |
| Tool definitions | `tools/base.py` + `tools/custom_tools.py` | `@tool` decorator |
| Tracing setup | `tracing/` | OpenTelemetry spans → StatsStore |

## KEY PATTERNS
- **Provider plugin**: `interface.py` ABC → implementations → factory in `__init__.py` → `@ProviderRegistry.register_service`
- **Graph nodes**: Thin state transformers → delegate to `services/`. Never put business logic in nodes.
- **ServicePool**: Globally shared engines (LLM/TTS/ASR) vs per-session (VAD, memory, emotion)
- **ConfigStore**: Workaround for LangGraph config limitation — use `state.get("_config", {})`

## NOTES
- 202 Python files, 30.4K lines, max depth 3
- `orchestration/server/routes.py` at 1092 lines is the critical hotspot
- All provider configs at `config/providers/{type}/` mirror `services/{speech,intelligence}/{type}/`
- Legacy compat sections exist in `memory/` (tagged `# ── legacy compat ──`)
