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
# Start all services (backend + frontend)
python scripts/start.py

# Start with options
python scripts/start.py --skip-frontend   # Backend only
python scripts/start.py --skip-backend    # Frontend only
python scripts/start.py --install         # Reinstall dependencies

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

# Run frontend dev server (from frontend/)
pnpm dev
```

### Training (Optional)
```bash
# Install training dependencies
pip install -r requirements-training.txt

# Collect training data
python scripts/training/collect_data.py

# Train model
python scripts/training/train_lightning.py
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
├── services/             # Service implementations
│   ├── asr/             # Speech recognition (FasterWhisper, GLM, OpenAI)
│   ├── tts/             # Speech synthesis (Edge TTS, GLM, OpenAI)
│   ├── llm/             # Language models (GLM, OpenAI, Ollama, LocalLoRA)
│   ├── vad/             # Voice activity detection (Silero)
│   └── conversation/    # Orchestrator for dialogue flow
├── pipeline/             # Chain-of-responsibility processing
│   ├── input_pipeline.py   # ASRStep -> TextCleanStep -> EmotionExtractionStep
│   ├── output_pipeline.py  # Sentence splitting, TTS scheduling
│   └── steps/              # Individual pipeline steps
├── events/               # Event-driven architecture
│   ├── core/bus.py      # EventBus for pub/sub
│   ├── core/router.py   # EventRouter for handler registration
│   └── handlers/        # Event handlers (text, audio, Live2D)
├── memory/               # Conversation memory
│   ├── memory_system.py # Unified memory interface
│   ├── short_term.py    # Rolling window context
│   ├── long_term.py     # Persistent storage
│   └── vector_store.py  # Semantic search with sentence-transformers
├── avatar/               # Live2D expression analysis
│   ├── analyzers/       # Keyword-based and LLM-based emotion extraction
│   └── strategies/      # Duration, intensity, position-based strategies
└── utils/                # Helpers (env, logging, auto-config)
```

### Frontend (Next.js/React/Socket.IO)

```
frontend/
├── app/                  # Next.js App Router
├── components/           # Reusable UI components (shadcn/ui + Radix)
├── features/             # Feature-specific components
├── hooks/                # Custom React hooks
└── shared/               # Shared utilities
```

### Data Flow

```
User Input (text/audio)
    ↓
InputPipeline: ASRStep → TextCleanStep → EmotionExtractionStep
    ↓
Agent.chat_stream() → LLM streaming response
    ↓
OutputPipeline: Sentence splitting → TTS synthesis
    ↓
EventBus.emit(sentence/audio/expression)
    ↓
Handlers: WebSocket send to frontend
    ↓
Frontend: Text display + Audio playback + Live2D sync
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

## Key Patterns

### Adding a New LLM Provider
1. Create config class in `src/anima/config/providers/llm/my_llm.py`
2. Create service in `src/anima/services/llm/implementations/my_llm.py`
3. Register with decorators:
```python
@ProviderRegistry.register_config("llm", "my_llm")
class MyLLMConfig(LLMBaseConfig):
    ...

@ProviderRegistry.register_service("llm", "my_llm")
class MyLLMAgent(LLMInterface):
    ...
```
4. Add config in `config/services.yaml` under `llm:` section

### Pipeline Steps
All pipeline steps inherit from `PipelineStep` and implement `async def process(self, ctx: PipelineContext)`:
```python
class MyStep(PipelineStep):
    @property
    def name(self) -> str:
        return "my_step"

    async def process(self, ctx: PipelineContext) -> None:
        # Modify ctx in place
        ctx.text = process_text(ctx.text)
```

### Event Handlers
Register handlers with `EventRouter`:
```python
@router.on("sentence", priority=EventPriority.HIGH)
async def handle_sentence(event: OutputEvent):
    await websocket.send(json.dumps({...}))
```

## Ports

- Backend: 12394 (Socket.IO + FastAPI)
- Frontend: 3000 (Next.js dev server)

## Skills

Use the `live2d` skill when working with Live2D models, expressions, lip sync, or the pixi-live2d-display library.
