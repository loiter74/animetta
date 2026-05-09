# ANIMA PROJECT KNOWLEDGE BASE

**Generated:** 2026-05-10
**Commit:** ff90d6d
**Branch:** main

> Primary knowledge base: [CLAUDE.md](CLAUDE.md). This AGENTS.md is the quick-reference map.

## OVERVIEW

AI virtual companion / VTuber framework. Python backend (FastAPI + LangGraph + Socket.IO) + Vue 3 Electron frontend + Live2D avatar.

## STRUCTURE

```
./
├── src/anima/              # Python backend (199 files, 29.7K lines)
│   ├── core/               # Entry point + service container
│   ├── orchestration/      # LangGraph state graph + WebSocket server
│   ├── services/           # LLM / ASR / TTS / VAD implementations
│   ├── memory/             # Wiki-architecture memory (Chroma + SQLite)
│   ├── config/             # Pydantic configs + provider registry
│   ├── avatar/             # Live2D emotion/expression analysis
│   ├── tools/              # Tool calling + MCP bridge
│   └── utils/              # Helpers
├── frontend/               # Vue 3 + TypeScript + Electron (UnoCSS, Pinia)
├── config/                 # YAML config files (personas, services, tools)
├── tests/                  # pytest suite (20 test files, 81 tests)
├── docs/                   # ADRs, plans, benchmarks
├── scripts/                # start.py, stop.py, etc.
└── .claude/                # Claude skills
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add LLM provider | `src/anima/services/intelligence/llm/` | Create class, register via `@ProviderRegistry` |
| Add ASR/TTS provider | `src/anima/services/speech/{asr,tts}/` | Same pattern as LLM |
| Add graph node | `src/anima/orchestration/graph/` | Follow node pattern in `__init__.py` |
| Add tool | `src/anima/tools/base.py` or `custom_tools.py` | Use `@tool` decorator |
| Add persona | `config/personas/` + `src/anima/config/persona/` | YAML + Pydantic |
| Fix WebSocket route | `src/anima/orchestration/server/routes.py` | **1092 lines - largest file** |
| Change memory behavior | `src/anima/memory/` | Wiki architecture, see ADR-005 |
| Fix Live2D expression | `src/anima/avatar/` + `frontend/src/components/live2d/` | |
| Run tests | `PYTHONPATH=src python -m pytest tests/ -v` | asyncio_mode=auto |
| Type check | `mypy src/ --ignore-missing-imports` | |

## CONVENTIONS

- **Python 3.13+** — `X | None` not `Optional[X]`
- **Pydantic V2** — `model_config = ConfigDict(...)` not `class Config:`
- **Async-first** — all I/O is async
- **Type hints required** on all public functions
- **Logging**: `loguru` logger, English only
- **Provider plugin pattern**: `interface.py` ABC → implementations → factory → `__init__.py` re-exports
- **TDD preferred** — write tests first

## ANTI-PATTERNS (THIS PROJECT)

- ❌ Never import from removed modules: `pipeline/`, `events/`, `handlers/`, `adapters/`, old `core/`, `services/conversation/`, old `state/`
- ❌ Never rewrite business logic in graph nodes — reuse `services/` implementations
- ❌ Never call `ctx.close()` on ServicePool — destroys shared LLM/TTS/ASR engines
- ❌ Never use real-time `getBounds()` in Live2D scaling — use cached `baseBounds`
- ❌ Never add EventBus back — LangGraph is the only orchestration mode (ADR-001)
- ❌ Pydantic V2 only — `class Config:` is forbidden

## COMMANDS

```bash
# Start all services
python scripts/start.py

# Backend only
python -m anima.socketio_server

# Tests
PYTHONPATH=src python -m pytest tests/ -v
PYTHONPATH=src python -m pytest tests/ --cov=src/anima --cov-report=term-missing

# Type + lint
mypy src/ --ignore-missing-imports
ruff check src/ tests/
```

## NOTES

- `docs/README.md` is OUTDATED — still references `adapters/`, `pipeline/`, `events/`
- `orchestration/server/routes.py` at 1092 lines is a known hotspot — thin dispatch preferred
- Coverage at ~21%, targeting 70%. No frontend tests exist.
- 5 ADRs in `docs/adrs/`: LangGraph, Hybrid Search, Plugin Architecture, Streaming, Wiki Memory
