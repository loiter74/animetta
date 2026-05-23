# ORCHESTRATION — LANGGRAPH + WEBSOCKET SERVER

**Generated:** 2026-05-23
**Commit:** 8930c5f

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW

LangGraph state graph engine + Socket.IO WebSocket server. The core request processing pipeline. 41 files total (21 graph/ + 8 server/ + 12 handlers/).

## STRUCTURE

```
orchestration/
├── graph/                   # State graph definition + nodes
│   ├── state.py             # AgentState TypedDict
│   ├── builder.py           # StateGraph builder (node wiring)
│   ├── orchestrator.py      # LangGraphOrchestrator — 388 lines
│   ├── llm_node.py          # LLM reasoning + RAG + tools — 388 lines
│   ├── asr_node.py          # Speech recognition node
│   ├── tts_node.py          # Speech synthesis node
│   ├── tool_node.py         # Tool execution node
│   ├── emotion_node.py      # Emotion analysis node
│   ├── output_node.py       # Output + memory storage — 309 lines
│   ├── personality_node.py  # Persona injection
│   ├── memory_middleware.py # Memory context RAG middleware
│   ├── interrupt_handler.py # User interrupt handling
│   ├── tool_manager.py      # Tool registration + dispatch
│   ├── scheduler.py         # Activity scheduling
│   ├── observability.py     # Langfuse/tracing hooks
│   ├── stats_handler.py     # StatsCallbackHandler
│   ├── stats_store.py       # SQLite stats persistence — 360 lines
│   ├── translation_state.py # Subtitle translation state
│   └── vc_node.py           # Voice conversion node
└── server/                  # Socket.IO + REST API
    ├── routes.py            # 383 lines — thinned by handler extraction
    ├── session.py           # Session management — 314 lines
    ├── lifecycle.py         # Session lifecycle hooks
    ├── live2d.py            # Live2D WebSocket events
    ├── desktop.py           # Desktop app integration
    ├── websocket.py         # WebSocket connection manager
    ├── stats_api.py         # Stats REST endpoints
    └── handlers/            # Domain-specific event handlers
        ├── base_handler.py         # Base handler abstract class
        ├── chat_handlers.py        # Message send/receive
        ├── bilibili_handlers.py    # Bilibili danmaku bridge
        ├── config_handlers.py      # Runtime config updates
        ├── lifecycle_handlers.py   # Session lifecycle events
        ├── live2d_handlers.py      # Live2D expression control
        ├── meme_handlers.py        # Meme pool interaction
        ├── memory_handlers.py      # Memory CRUD operations
        ├── minecraft_handlers.py   # Minecraft bot control
        ├── persona_handlers.py     # Persona switching
        └── singing_handlers.py     # Singing request management
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add a graph node | `graph/` | Follow `__init__.py` docstring pattern |
| Change state shape | `graph/state.py` | TypedDict — propagate to all node signatures |
| Fix routing logic | `server/routes.py` | Thin dispatch — handlers in `server/handlers/` |
| Add a new handler | `server/handlers/` | Extend `BaseHandler`, register in routes.py |
| Session lifecycle | `server/session.py` | `Session` class wraps orchestrator per user |
| Observability | `graph/observability.py` | Langfuse + OpenTelemetry integration |
| Stats/queries | `graph/stats_store.py` + `server/stats_api.py` | SQLite backend + REST API |

## KEY PATTERNS

- **Node function signature**: `async def x_node(state: AgentState) -> dict[str, Any]`
- **State access**: `state.get("_config", {})` for ConfigStore, `state["messages"]` for history
- **Node responsibility**: State transformation only — call `services/` for business logic
- **Builder pattern**: `graph/builder.py` wires nodes into the StateGraph with conditional edges

## ANTI-PATTERNS

- ❌ Never put business logic in nodes — delegate to `services/`
- ❌ Never import from removed modules (`pipeline/`, `events/`, old `core/`)
- ❌ Never add EventBus back — LangGraph is the only orchestration mode

## NOTES

- `routes.py` was thinned from 1092 to 383 lines by extracting domain handlers into `server/handlers/`. New handlers should follow the same pattern.
- `orchestrator.py` (388 lines) and `llm_node.py` (388 lines) are the next largest modules.
- `stats_store.py` (360 lines) has its own schema migration system (`_migrate_schema`).
- `vc_node.py` (210 lines) handles voice conversion between ASR and TTS stages.
- Graph nodes should be kept under ~200 lines — refactor if they grow beyond that.
