# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Anima is a configurable AI virtual companion / VTuber framework with Live2D avatar support. It features:
- Plugin-based architecture with decorator-based service registration
- Profile-driven configuration (switch between LLM/ASR/TTS providers)
- **LangGraph state graph for dialogue orchestration** (migrated from EventBus)
- Streaming response support for LLM and TTS
- Memory system with vector storage for long-term context
- Tool calling support with MCP protocol integration

## Commands

### Running the Application
```bash
# Start all services (default: backend + web config + desktop app)
python scripts/start.py

# Start with mode selection
python scripts/start.py --mode desktop   # Electron desktop app (default)
python scripts/start.py --mode web       # Web mode (requires pnpm)

# Start with options
python scripts/start.py --backend-only   # Backend only (port 12394)
python scripts/start.py --no-backend     # Skip backend
python scripts/start.py --no-web-config  # Skip web config interface
python scripts/start.py --no-app         # Skip desktop/web app
python scripts/start.py --install        # Reinstall dependencies

# Stop all services
python scripts/stop.py

# Run backend directly
python -m anima.socketio_server
```

### Development
```bash
# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies (from frontend/)
cd frontend && pnpm install

# Run Electron app (from frontend/)
pnpm dev              # Development mode with HMR
pnpm build            # Build for production
pnpm typecheck        # TypeScript type checking
```

## Architecture

### Backend (Python/FastAPI/Socket.IO)

```
src/anima/
├── socketio_server.py    # Main entry point, WebSocket server
├── service_context.py    # Service container, manages ASR/TTS/LLM instances
├── config/               # Configuration loading (YAML + Pydantic)
│   ├── app.py           # AppConfig - main configuration class
│   ├── persona.py       # PersonaConfig - character personality
│   ├── providers/       # Provider-specific config classes (ASR/TTS/LLM/VAD)
│   └── core/registry.py # Service registry for plugin architecture
├── graph/                # LangGraph state graph (NEW ARCHITECTURE)
│   ├── state.py         # AgentState definition
│   ├── builder.py       # StateGraph builder
│   ├── orchestrator.py  # LangGraphOrchestrator
│   ├── config_store.py  # Configuration storage for nodes
│   └── nodes/           # Graph nodes
│       ├── asr_node.py      # Speech recognition node
│       ├── llm_node.py      # LLM reasoning node (with RAG + tools)
│       ├── tts_node.py      # Speech synthesis node
│       ├── emotion_node.py  # Emotion analysis node
│       ├── output_node.py   # Output to frontend + memory storage
│       └── tool_node.py     # Tool execution node
├── tools/                # Tool calling system
│   ├── base.py          # Built-in tools
│   ├── config.py        # Tool configuration loader
│   └── mcp_bridge.py    # MCP protocol bridge
├── services/             # Service implementations
│   ├── asr/             # Speech recognition (FasterWhisper, GLM, OpenAI)
│   ├── tts/             # Speech synthesis (Edge TTS, GLM, OpenAI)
│   ├── llm/             # Language models (GLM, OpenAI, Ollama, LocalLoRA)
│   │   └── langchain_adapter.py  # LangChain ChatModel adapter
│   ├── vad/             # Voice activity detection (Silero)
│   ├── live2d/          # Live2D action queue, viseme sync, preset loader
│   └── audio/           # Audio processing utilities
├── memory/               # Conversation memory (OpenClaw-style architecture)
│   ├── memory_system.py # Unified memory interface
│   ├── memory_manager.py # Core manager (index/sync/search)
│   ├── memory_turn.py   # Memory turn data structure
│   ├── config.py        # Configuration (ChunkConfig, SearchConfig)
│   ├── models.py        # Data models (Chunk, SearchResult, FileEntry)
│   ├── chunker.py       # Markdown sliding-window chunking
│   ├── sqlite_store.py  # SQLite FTS5 + metadata storage
│   ├── chroma_store.py  # Chroma vector storage
│   └── hybrid_search.py # Hybrid search (vector 70% + keyword 30%)
├── avatar/               # Live2D expression analysis
│   ├── analyzers/       # Keyword-based and LLM-based emotion extraction
│   └── strategies/      # Duration, intensity, position-based strategies
├── server/               # Server lifecycle management
│   ├── lifecycle.py     # Server startup/shutdown
│   ├── session.py       # Session management (orchestrator factory)
│   ├── routes.py        # WebSocket route handlers
│   ├── desktop.py       # Desktop-specific routes
│   └── live2d.py        # Live2D-specific routes
└── utils/                # Helpers (env, logging, auto-config)
```

### Frontend (Electron + Vue 3 + TypeScript)

Electron desktop app built with Vue 3, TypeScript, UnoCSS, and Pinia.

**Tech Stack:** electron-vite, Vue 3 (Composition API), TypeScript, UnoCSS, Pinia, pixi.js

```
frontend/
├── electron/              # Electron main process (TypeScript)
│   ├── main.ts           # Application entry point
│   ├── preload.ts        # Context bridge (exposes window.electronAPI)
│   ├── ipc-bridge.ts     # Socket.IO client ↔ IPC relay
│   └── window-manager.ts # BrowserWindow creation
├── src/                   # Vue 3 renderer process
│   ├── App.vue           # Root component
│   ├── main.ts           # Vue entry (Pinia + UnoCSS)
│   ├── components/       # Vue components
│   │   ├── chat/         # ChatPanel, MessageList, InputBar, VoiceButton
│   │   ├── live2d/       # Live2DRenderer, PopOutButton, useLive2D
│   │   ├── layout/       # AppLayout, TitleBar
│   │   └── shared/       # GlassPanel, AnimatedButton
│   ├── composables/      # Vue Composables (useSocket, useChat, useVoice)
│   ├── stores/           # Pinia stores (chat, connection)
│   ├── types/            # TypeScript types (chat, live2d, socket-events)
│   └── styles/           # Global styles + animations
├── public/live2d/        # Live2D models + Cubism Core
├── electron.vite.config.ts
├── uno.config.ts         # UnoCSS theme (anime color tokens)
├── tsconfig.json
└── package.json
```

**Architecture:** Single window with Live2D + Chat side-by-side. Live2D can be popped out to a separate window. Socket.IO runs in main process, events relayed to renderer via IPC.

### Data Flow (LangGraph Architecture)

```
User Input (WebSocket)
    ↓
[START] → route_input()
    │
    ├── (audio) → [asr_node] → speech recognition
    │                       → updates state["user_text"]
    │
    └── (text) ──────────────────→ [llm_node]
                                      │
                                      ├── RAG: retrieves memory context
                                      ├── Builds prompt with persona
                                      ├── Calls LLM with tools
                                      │
                             ┌────────┴────────┐
                             │                 │
                       (tool_calls)     (direct reply)
                             │                 │
                        [tool_node]      [tts_node]
                             │                 │
                        execute tools     TTS synthesis
                             │                 │
                        results ──────────────┤
                                               ↓
                                         [emotion_node]
                                               ↓
                                         [output_node]
                                               ↓
                                    Socket.IO → Frontend
                                               ↓
                                    Store to memory
                                               ↓
                                         [END]
```

**Note:** Each node reads/updates `AgentState` (TypedDict). The `LangGraphOrchestrator` manages graph execution via `graph.astream()` or `graph.ainvoke()`.

## LangGraph Architecture

### AgentState

The central state object passed between nodes:

```python
class AgentState(TypedDict):
    # Input
    input_type: str                    # 'text' or 'audio'
    raw_audio: Optional[bytes]         # Audio data
    user_text: str                     # User text (from input or ASR)

    # LLM conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]  # Message history
    system_prompt: Optional[str]       # System prompt with persona

    # Tool calling
    tool_calls: Optional[List[Dict]]   # Tool requests from LLM
    tool_results: Optional[List[Dict]] # Tool execution results

    # Output
    response_text: str                 # Final LLM response
    response_chunks: List[str]         # Streaming chunks
    tts_audio: Optional[bytes/str]     # TTS audio data
    emotion: Optional[str]             # Emotion label

    # Metadata
    session_id: str
    persona: Optional[Dict]
    channel_id: Optional[str]
    user_id: Optional[str]
    user_name: Optional[str]
    metadata: Dict[str, Any]
```

### Node Implementation Pattern

All nodes follow this pattern:

```python
async def my_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Node function

    Args:
        state: Current state (read/write)
        config: LangGraph config (contains _config with service_context, etc.)

    Returns:
        Updated state (or partial state dict)
    """
    # Get service context from internal config
    internal_config = state.get("_config", {})
    service_context = internal_config.get("service_context")

    # Read from state
    user_text = state.get("user_text", "")

    # Process...
    result = process(user_text)

    # Return updated state
    return {"response_text": result}
```

### Graph Builder

```python
from anima.graph.builder import build_graph

# Build graph with tools
graph = build_graph(
    checkpointer=MemorySaver(),  # Optional state persistence
    enable_tools=True,
    tools=langchain_tools,
    tools_map=tools_map,
)

# Compile and use
compiled = graph.compile()
result = await compiled.ainvoke(initial_state)
```

### Orchestrator Usage

```python
from anima.graph.orchestrator import LangGraphOrchestratorFactory

# Create orchestrator
orchestrator = await LangGraphOrchestratorFactory.create(
    session_id="user-123",
    service_context=service_context,
    socketio=sio,
    emotion_analyzer=emotion_analyzer,
    enable_tools=True,  # Enable tool calling
    tools_config=tools_config,
)

# Process input
await orchestrator.process_text(text="你好", user_id="user", user_name="Alice")
await orchestrator.process_audio(audio_data=b"...")
```

## Tool System

### Built-in Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `web_search` | `query: str`, `num_results: int` | Internet search |
| `get_weather` | `city: str` | Weather query |
| `read_file` | `file_path: str`, `max_length: int` | Read file contents |
| `get_current_time` | `timezone: str` | Get current time |
| `list_directory` | `directory: str` | List directory |
| `calculator` | `expression: str` | Math calculation |

### Tool Configuration

`config/tools.yaml`:
```yaml
builtin_tools:
  - web_search
  - calculator

mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "./data"]

tool_settings:
  max_tool_calls_per_turn: 5
  tool_execution_timeout: 30
```

### Custom Tool Example

```python
from langchain_core.tools import tool

@tool
async def my_tool(param: str) -> str:
    """Tool description for LLM."""
    return f"Result: {param}"

# Register in orchestrator
tools, tools_map = create_tool_registry(
    builtin_enabled=["calculator"],
    extra_tools=[my_tool],
)
```

## Memory System Architecture

The memory system follows an OpenClaw-style architecture with Markdown as the single source of truth.

### Storage Layers

1. **Short-term Memory**: In-memory session cache (configurable max turns, default 20)
2. **Long-term Memory**:
   - **Markdown Files**: Primary storage (`MEMORY.md` + daily logs in `YYYY-MM-DD.md`)
   - **SQLite FTS5**: Full-text search index with metadata
   - **Chroma**: Vector embeddings for semantic search

### Retrieval Strategy

Hybrid search combining:
- **Vector semantic search** (70% weight): Finds conceptually similar content
- **BM25 keyword search** (30% weight): Finds exact keyword matches

### RAG Integration

Memory is automatically integrated into the LangGraph flow:
- **Retrieval**: In `llm_node.py`, before LLM call: `_retrieve_memory_context()`
- **Storage**: In `output_node.py`, after response: `_store_conversation_to_memory()`

```python
# llm_node.py - RAG retrieval
memory_context = await memory.retrieve_context(
    query=state["user_text"],
    session_id=state["session_id"],
    max_turns=5,
)

# output_node.py - Memory storage
await memory.store_turn(MemoryTurn(
    session_id=state["session_id"],
    user_input=state["user_text"],
    agent_response=state["response_text"],
    emotions=[state.get("emotion")],
))
```

## Configuration

### Main Config (`config/config.yaml`)
```yaml
persona: "neuro-vtuber"   # Character personality
services:
  asr: faster_whisper     # Speech recognition
  tts: edge               # Speech synthesis
  agent: glm              # Main LLM (with persona)
  local_llm: local_lora   # Optional: local fine-tuned model
  vad: silero             # Voice activity detection
system:
  host: "0.0.0.0"
  port: 12394
```

### Service Config (`config/services.yaml`)
Contains detailed configurations for all service providers (ASR, TTS, LLM, VAD).

### Personas (`config/personas/`)
Define character personality, speaking style, and behavior rules.

### Environment Variables (`.env`)
```bash
GLM_API_KEY=xxx           # Zhipu AI API key
OPENAI_API_KEY=xxx        # OpenAI API key (optional)
ANIMA_BASE_MODEL_PATH=xxx # For local LoRA
ANIMA_LORA_PATH=xxx       # For local LoRA
```

## Key Patterns

### Adding a New Service Provider

1. Create config class in `src/anima/config/providers/llm/my_llm.py`
2. Create service in `src/anima/services/llm/implementations/my_llm.py`
3. Register with decorators:
```python
@ProviderRegistry.register_config("llm", "my_llm")
class MyLLMConfig(LLMBaseConfig):
    ...

@ProviderRegistry.register_service("llm", "my_llm")
class MyLLMAgent(LLMInterface):
    @classmethod
    def from_config(cls, config, **kwargs):
        return cls(api_key=config.api_key, model=config.model)
```

### Adding a New Graph Node

1. Create node function in `src/anima/graph/nodes/my_node.py`:
```python
from anima.graph.state import AgentState
from langgraph.graph import RunnableConfig

async def my_node(state: AgentState, config: RunnableConfig) -> AgentState:
    # Get internal config
    internal_config = state.get("_config", {})
    service_context = internal_config.get("service_context")

    # Process
    result = process_data(state["input_field"])

    # Return updated state
    return {"output_field": result}
```

2. Register in `src/anima/graph/nodes/__init__.py`:
```python
from .my_node import my_node
```

3. Add to graph in `src/anima/graph/builder.py`:
```python
graph.add_node("my_node", my_node)
graph.add_edge("previous_node", "my_node")
```

### ConfigStore Pattern

LangGraph's config system doesn't pass all needed data to nodes. Use `ConfigStore` for node access:

```python
from anima.graph.config_store import ConfigStore

# Set config (in orchestrator)
ConfigStore.set(session_id, "service_context", service_context)
ConfigStore.set(session_id, "socketio", sio)

# Get config (in node)
service_context = ConfigStore.get(state["session_id"], "service_context")
```

## WebSocket Events

**Client → Server:**
- `text_input` - `{text: string, from_name?: string}`
- `raw_audio_data` - `{audio: float32[]}` (VAD mode)
- `mic_audio_end` - Signal end of audio input
- `interrupt_signal` - `{heard_text?: string}`

**Server → Client:**
- `text` - `{text: string, seq: number}`
- `audio` - `{data: base64, format: string}`
- `audio_with_expression` - `{audio_path: str, text: str, emotions: [], volumes: []}`
- `expression` - `{expression: str}`
- `control` - `{signal: string}` (conversation-start, conversation-end, interrupt)
- `transcript` - `{text: string, is_final: boolean}`

## Ports

- Backend: 12394 (Socket.IO + FastAPI)
- Web Config: 8080 (HTTP)
- Frontend: Electron desktop app (no port)

## Skills

Use the `live2d` skill when working with Live2D models, expressions, lip sync, or the pixi-live2d-display library.

## Migration Notes

### From Vanilla JS to Vue 3 + TypeScript (Completed)

The frontend was migrated from pure Electron + vanilla JS/HTML/CSS to Vue 3 + TypeScript + electron-vite.

- Old frontend backed up at `frontend-legacy/`
- New frontend at `frontend/` (Vue 3 + TypeScript + UnoCSS + Pinia)
- See `openspec/changes/vue3-frontend-migration/` for design decisions and task tracking

### From EventBus to LangGraph (Completed)

The following modules have been **removed**:
- `src/anima/pipeline/` - Pipeline processing
- `src/anima/events/` - EventBus system
- `src/anima/handlers/` - Event handlers
- `src/anima/adapters/` - Adapter layer
- `src/anima/core/` - Core abstractions
- `src/anima/services/conversation/` - Old orchestrator
- `src/anima/state/` - Old state modules

Replaced by:
- `src/anima/graph/` - LangGraph state graph
- `src/anima/tools/` - Tool system with MCP support

See [docs/LANGGRAPH_MIGRATION_COMPLETE.md](docs/LANGGRAPH_MIGRATION_COMPLETE.md) for details.

## Related Documentation

- [LangGraph Migration Complete](docs/LANGGRAPH_MIGRATION_COMPLETE.md)
- [Tools System](docs/TOOLS.md)
- [Live2D System](MEMORY.md#live2d-lip-sync-system-2025-03)
