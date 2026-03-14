# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Anima is a configurable AI virtual companion / VTuber framework with Live2D avatar support. It features:
- Plugin-based architecture with decorator-based service registration
- Profile-driven configuration (switch between LLM/ASR/TTS providers)
- Streaming response support for LLM and TTS
- Memory system with vector storage for long-term context
- Pipeline-based data processing with event-driven architecture

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
cd frontend && npm install

# Run Electron app (from frontend/)
npm run dev          # Development mode with dev tools
npm start            # Production mode
npm run build:win    # Build for Windows
```

## Architecture

### Backend (Python/FastAPI/Socket.IO)

```
src/anima/
├── socketio_server.py    # Main entry point, WebSocket handlers
├── service_context.py    # Service container, manages ASR/TTS/LLM instances
├── config/               # Configuration loading (YAML + Pydantic)
│   ├── app.py           # AppConfig - main configuration class
│   ├── persona.py       # PersonaConfig - character personality
│   ├── providers/       # Provider-specific config classes (ASR/TTS/LLM/VAD)
│   └── core/registry.py # Service registry for plugin architecture
├── adapters/             # Channel adapter layer (input/output abstraction)
│   ├── base.py          # ChannelAdapter base class
│   ├── registry.py      # AdapterRegistry singleton
│   └── implementations/ # DesktopLive2DChatter (Electron desktop)
├── services/             # Service implementations
│   ├── asr/             # Speech recognition (FasterWhisper, GLM, OpenAI)
│   ├── tts/             # Speech synthesis (Edge TTS, GLM, OpenAI)
│   ├── llm/             # Language models (GLM, OpenAI, Ollama, LocalLoRA)
│   ├── vad/             # Voice activity detection (Silero)
│   ├── live2d/          # Live2D action queue, viseme sync, preset loader
│   └── conversation/    # Orchestrator for dialogue flow
├── pipeline/             # Chain-of-responsibility processing
│   ├── base.py          # PipelineStep base class
│   └── steps/           # Individual pipeline steps (ASR, text clean, etc.)
├── events/               # Event-driven architecture
│   ├── bus.py           # EventBus for pub/sub
│   ├── router.py        # EventRouter for handler registration
│   └── models.py        # OutputEvent, EventType definitions
├── handlers/             # Event handlers
│   ├── base.py          # Handler base classes
│   ├── registry.py      # Handler registration utilities
│   ├── text.py          # TextHandler (output)
│   ├── unified.py       # UnifiedEventHandler (audio + expression)
│   ├── input_handler.py # InputHandler (INPUT_* → Orchestrator)
│   └── adapters/        # Socket adapter handlers
├── memory/               # Conversation memory (OpenClaw-style architecture)
│   ├── memory_system.py # Unified memory interface (backward compatible)
│   ├── memory_manager.py # Core manager (index/sync/search)
│   ├── memory_turn.py   # Memory turn data structure
│   ├── config.py        # Configuration (ChunkConfig, SearchConfig, MemoryConfig)
│   ├── models.py        # Data models (Chunk, SearchResult, FileEntry)
│   ├── chunker.py       # Markdown sliding-window chunking
│   ├── sqlite_store.py  # SQLite FTS5 + metadata storage
│   ├── chroma_store.py  # Chroma vector storage
│   ├── hybrid_search.py # Hybrid search (vector 70% + keyword 30%)
│   └── tools.py         # Agent tool interfaces (memory_search/memory_get)
├── avatar/               # Live2D expression analysis
│   ├── analyzers/       # Keyword-based and LLM-based emotion extraction
│   └── strategies/      # Duration, intensity, position-based strategies
├── state/                # Runtime state management
│   ├── audio_buffer.py  # Audio buffer management
│   └── tts_task_manager.py
├── server/               # Server lifecycle management
│   ├── lifecycle.py     # Server startup/shutdown
│   ├── session.py       # Session management
│   ├── websocket.py     # WebSocket handlers
│   ├── routes.py        # HTTP routes
│   ├── desktop.py       # Desktop-specific routes
│   └── live2d.py        # Live2D-specific routes
└── utils/                # Helpers (env, logging, auto-config)
```

### Frontend (Electron)

Pure Electron app with vanilla JS/HTML/CSS (no React/Next.js).

```
frontend/
├── main/                  # Electron main process
│   ├── index.js          # Application entry point
│   ├── windows/          # Window management (Live2DWindow, ChatWindow)
│   ├── ipc/              # Inter-process communication handlers
│   └── config/           # App configuration
├── renderer/             # Renderer processes (vanilla JS/HTML/CSS)
│   ├── chat/             # Chat window
│   ├── live2d/           # Live2D viewer (pixi-live2d-display)
│   └── shared/           # Shared utilities and constants
├── preload/
│   └── index.js          # Preload script (context bridge)
└── package.json          # Dependencies: electron, pixi.js, pixi-live2d-display
```

### Data Flow

```
External Input (WebSocket from Electron/Frontend)
    ↓
Adapter Layer: DesktopLive2DChatter
    │   ├── send_text() → EventBus.emit(INPUT_TEXT)
    │   ├── send_audio() → EventBus.emit(INPUT_AUDIO)
    │   ├── handle_audio_chunk() → VAD detection → buffer accumulation
    │   └── handle_audio_end() → EventBus.emit(INPUT_AUDIO)
    ↓
EventBus → InputHandler → Orchestrator.process_input()
    ↓
Orchestrator's InputPipeline: ASRStep → TextCleanStep → LocalLLMStep
    ↓
Agent.chat_stream() → LLM streaming response
    ↓
Orchestrator's OutputPipeline: Sentence splitting → TTS synthesis → EmotionExtraction
    ↓
EventBus.emit(sentence/audio/expression/control)
    ↓
Adapter.send(event) → WebSocket emit
    ↓
Frontend: Text display + Audio playback + Live2D sync
```

**Note:** The Orchestrator creates and manages InputPipeline/OutputPipeline internally. Each Orchestrator instance has its own EventBus and EventRouter for isolated session handling.

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

### Chunking

Sliding window chunking with:
- Target: ~400 tokens per chunk
- Overlap: 80 tokens between chunks
- Incremental indexing based on file hash detection

### Key Components

```python
# Storing a conversation turn
await memory.store_turn(MemoryTurn(
    session_id="session-001",
    user_input="Hello",
    agent_response="Hi there!",
    emotions=["happy"],
    importance=0.5,  # High importance (>=0.7) also saved to MEMORY.md
))

# Retrieving context
results = await memory.retrieve_context(
    query="what did we talk about",
    session_id="session-001",
    max_turns=5,
)
```

### Graceful Degradation

If MemoryManager initialization fails (missing dependencies, etc.), the system falls back to pure in-memory mode with a warning log.

## EventBus Architecture

The EventBus is the central communication hub. All components communicate through it.

### Subscription Pattern
```python
# Subscribe to specific event type
sub = event_bus.subscribe("sentence", handler, priority=EventPriority.HIGH)

# Subscribe to all events
sub = event_bus.subscribe_all(handler)

# Unsubscribe
event_bus.unsubscribe(sub)
```

### Event Types

**Input Events** (from Adapter to Orchestrator):
- `INPUT_TEXT` - Text input from user
- `INPUT_AUDIO` - Audio input (after VAD/accumulation)
- `INTERRUPT` - User interruption signal

**Output Events** (from Orchestrator to Adapter):
- `sentence` - Text sentence (streaming)
- `audio` - TTS audio data
- `audio_with_expression` - Audio combined with Live2D expression
- `control` - Control signals (conversation-start, conversation-end, etc.)
- `expression` - Live2D expression/motion command
- `tool_call` - Tool execution request

### OutputEvent Structure
```python
@dataclass
class OutputEvent:
    type: str                    # Event type
    data: Any                    # Event payload
    seq: int = 0                 # Sequence number for ordering
    metadata: Dict[str, Any] = field(default_factory=dict)  # channel_id, session_id, etc.
```

### Event Data Format Conventions

**IMPORTANT:** Handlers must be defensive about `event.data` and `event.metadata` types.

| Event Type | `data` Type | `metadata` Keys |
|------------|-------------|-----------------|
| `sentence` | `str` (text content) | `is_complete: bool` (optional, marks end) |
| `audio` | `dict` with `path: str` | - |
| `audio_with_expression` | `dict` with `audio_path`, `emotions`, `text` | - |
| `expression` | `str` (expression name) | `timestamp: float` |
| `control` | `dict` with `signal: str` | - |
| `INPUT_TEXT` | `dict` with `content`, `user_id`, `user_name` | `channel_id`, `session_id` |
| `INPUT_AUDIO` | `dict` with `content` (audio array), `sample_rate` | `channel_id`, `session_id` |
| `INTERRUPT` | `dict` with `heard_text` | `channel_id`, `session_id` |

**Handler Implementation Pattern:**
```python
async def handle(self, event: "OutputEvent") -> None:
    # Defensive type checking for data
    data = event.data
    if not isinstance(data, dict):
        logger.error(f"[{self.name}] Expected dict, got {type(data).__name__}")
        return

    value = data.get("key", default)

    # Defensive type checking for metadata
    metadata = event.metadata
    if isinstance(metadata, dict):
        flag = metadata.get("flag", False)
    else:
        flag = False
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
Define character personality, speaking style, and behavior rules. Each persona includes:
- Identity and personality traits
- Speaking style and catchphrases
- Response examples
- Emoji and emotion tag usage

### Environment Variables (`.env`)
```bash
GLM_API_KEY=xxx           # Zhipu AI API key
OPENAI_API_KEY=xxx        # OpenAI API key (optional)
ANIMA_BASE_MODEL_PATH=xxx # For local LoRA
ANIMA_LORA_PATH=xxx       # For local LoRA
```

### Local Model Paths
- Base 7B model: `E:/anima_data/models/huggingface/models--Qwen--Qwen2.5-7B-Instruct/...`
- Style transfer LoRA: `E:/anima_data/models/style_transfer/final/lora`

## Key Patterns

### Adding a New Service Provider (LLM/ASR/TTS/VAD)
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
4. Add config in `config/services.yaml` under `llm:` section
5. Update `src/anima/services/llm/implementations/__init__.py` to export the class

**Service Factory Pattern:**
```python
# Type-safe creation from config
engine = LLMFactory.create_from_config(config=llm_config, system_prompt=prompt)

# Or with explicit provider
engine = ASRFactory.create(provider="faster_whisper", model="large-v3", ...)
```

### Pipeline Steps
All pipeline steps inherit from `PipelineStep` and implement `async def process(self, ctx: PipelineContext)`:

**PipelineContext fields:**
- `raw_input: Union[str, np.ndarray]` - Original input (text or audio)
- `text: str` - Processed text (filled by ASR or direct text input)
- `from_name: str` - Sender name
- `metadata: Dict[str, Any]` - Extra data (skip_history, skip_memory, etc.)
- `response: str` - Agent response (filled by AgentStep)
- `skip_remaining: bool` - Skip subsequent steps

```python
class MyStep(PipelineStep):
    @property
    def name(self) -> str:
        return "my_step"

    async def process(self, ctx: PipelineContext) -> None:
        # Modify ctx in place
        ctx.text = process_text(ctx.text)
        # Skip remaining steps if needed
        ctx.skip()
```

### Event Handlers
Register handlers with `EventRouter`:
```python
# Create router and register handlers
router = EventRouter(event_bus)
router.register("sentence", TextHandler(), priority=EventPriority.HIGH)
router.register("audio_with_expression", AudioExpressionHandler())
router.setup()  # Connect to EventBus

# Or use decorator pattern
@router.on("sentence", priority=EventPriority.HIGH)
async def handle_sentence(event: OutputEvent):
    await websocket.send(json.dumps({...}))
```

### Channel Adapters
Adapters convert external input to EventBus events and forward EventBus output to clients.

**Key principle:** Adapters only depend on EventBus, not on Orchestrator directly.

```python
from anima.adapters import ChannelAdapter, AdapterCapabilities

class DesktopLive2DChatter(ChannelAdapter):
    """Electron desktop app adapter with Live2D + voice/text chat"""

    @property
    def channel_type(self) -> str:
        return "desktop_live2d"

    @property
    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            text_input=True,
            voice_input=True,  # with VAD
            audio_output=True,
            streaming=True,
            interrupt=True,
        )

    async def start(self) -> None:
        self._subscribe_output()  # Subscribe to EventBus output events
        self._is_running = True

    async def stop(self) -> None:
        self._unsubscribe_output()
        self._is_running = False

    async def send(self, event: OutputEvent) -> None:
        """Send output event to client (called by EventBus)"""
        await self._send_callback(event.to_dict())

    # Input methods emit to EventBus
    async def send_text(self, text: str, **kwargs) -> None:
        await self._emit_input(event_type="INPUT_TEXT", content=text, ...)

    async def send_interrupt(self, heard_text: str = "") -> None:
        await self.event_bus.emit(OutputEvent(type="INTERRUPT", ...))
```

**Usage in socketio_server.py:**
```python
adapter = await get_or_create_adapter(sid)
await adapter.handle_text_input(text=text, ...)
await adapter.handle_audio_chunk(audio_chunk)
```

## Ports

- Backend: 12394 (Socket.IO + FastAPI)
- Web Config: 8080 (HTTP)
- Frontend: Electron desktop app (no port)

## WebSocket Events

Frontend-backend communication via Socket.IO:

**Client → Server:**
- `text_input` - `{text: string, from_name?: string}`
- `audio_data` - `{audio: float32[], sample_rate: number}`
- `audio_end` - Signal end of audio input
- `interrupt` - `{heard_text?: string}`

**Server → Client:**
- `text` - `{text: string, seq: number}`
- `audio` - `{data: base64, format: string}`
- `control` - `{signal: string}` (conversation-start, conversation-end, interrupt)
- `transcript` - `{text: string, is_final: boolean}`

## Skills

Use the `live2d` skill when working with Live2D models, expressions, lip sync, or the pixi-live2d-display library.

## Implementation Plans

- [ADAPTER_MCP_IMPLEMENTATION_PLAN.md](docs/plans/ADAPTER_MCP_IMPLEMENTATION_PLAN.md)
  - Adapter Layer: Input abstraction for multiple channels ✓ (implemented)
  - MCP Layer: Tool integration with permission management (planned)
