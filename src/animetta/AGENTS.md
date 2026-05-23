# ANIMA BACKEND — PYTHON PACKAGE

**Generated:** 2026-05-23
**Commit:** 8930c5f

> Parent: [../AGENTS.md](../AGENTS.md) — root project conventions and anti-patterns.

## OVERVIEW
Python backend for Anima VTuber — FastAPI + LangGraph + Socket.IO orchestration with plugin-based provider architecture. ~240 files, 30K+ lines, max depth 3.

## STRUCTURE
```
src/anima/
├── core/                    # Entry point + service container (6 files)
├── orchestration/           # → see orchestration/AGENTS.md
│   ├── graph/               # LangGraph nodes + orchestrator
│   └── server/              # WebSocket routes + sessions
├── services/                # → see services/AGENTS.md
│   ├── speech/{asr,tts}/    # Speech recognition + synthesis
│   ├── intelligence/{llm,vad}/  # Language models + voice activity
│   ├── audio/               # Audio processing pipeline
│   ├── singing/             # RVC/SVC singing pipeline
│   └── live/                # Bilibili danmaku livestream
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
├── tools/                   # Tool calling + MCP bridge + Minecraft bot
│   └── minecraft/           # ⚠️ Node.js bot (Mineflayer) inside Python tree
├── notifier/                # Alert channels (Discord, Feishu, Email)
├── inspection/              # Health/telemetry background checks
├── persistence/             # Thin, protocols.py only
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
| App config | `config/app.py` | Main config schema |
| Graph node template | `orchestration/graph/__init__.py` | Node docstring explains pattern |
| Tool definitions | `tools/base.py` + `tools/custom_tools.py` | `@tool` decorator |
| Singing pipeline | `services/singing/` | RVC/SVC pipeline + mixer |
| Minecraft bot | `tools/minecraft/` | ⚠️ Node.js bot in Python tree |
| Health checks | `inspection/` | Background periodic checks |
| Alert notifications | `notifier/` | Discord, Feishu, Email |
| Tracing setup | `tracing/` | OpenTelemetry spans → StatsStore |

## KEY PATTERNS
- **Provider plugin**: `interface.py` ABC → implementations → factory in `__init__.py` → `@ProviderRegistry.register_service`
- **Graph nodes**: Thin state transformers → delegate to `services/`. Never put business logic in nodes.
- **ServicePool**: Globally shared engines (LLM/TTS/ASR) vs per-session (VAD, memory, emotion)
- **ConfigStore**: Workaround for LangGraph config limitation — use `state.get("_config", {})`

## NOTES
- ~240 Python files, 30K+ lines, max depth 3
- `orchestration/server/routes.py` at 383 lines is the critical hotspot
- All provider configs at `config/providers/{type}/` mirror `services/{speech,intelligence}/{type}/`
- `tools/minecraft/bot/` is a Node.js package embedded in Python tree — cross-language hybrid
- Two runtime data dirs: `data/` (chroma_db, stats) + `memory_db/` (wiki, chroma, sqlite)
- Legacy compat sections exist in `memory/` (tagged `# ── legacy compat ──`)
