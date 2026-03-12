# Large Files Analysis & Refactoring Recommendations

This document analyzes files over 300 lines in the Anima codebase and provides refactoring recommendations.

**Analysis Date:** 2026-03-11

## Summary

| File | Lines | Complexity | Refactoring Priority |
|------|-------|------------|---------------------|
| socketio_server.py | 942 | High | **High** |
| orchestrator.py | 571 | Medium-High | Medium |
| desktop_live2d_chatter.py | 506 | Medium | Low |
| glm_llm.py | 477 | Medium | Low |
| intensity.py | 418 | Low | No |
| service_context.py | 379 | Medium | Low |

---

## 1. socketio_server.py (942 lines)

**Location:** `src/anima/socketio_server.py`

### Current Responsibilities

This file has **too many responsibilities** (violates Single Responsibility Principle):

1. **Server initialization** (lines 1-96)
   - Module path setup
   - Environment variable loading
   - Socket.IO server creation

2. **Global state management** (lines 117-156)
   - Session contexts dictionary
   - Orchestrators dictionary
   - Adapters dictionary
   - Desktop clients tracking
   - Live2D action queue

3. **Session/Context factories** (lines 191-390)
   - `get_or_create_context()` - ServiceContext factory
   - `get_or_create_orchestrator()` - Orchestrator factory
   - `cleanup_context()` - Resource cleanup
   - `get_or_create_adapter()` - Adapter factory

4. **Socket.IO event handlers** (lines 397-800)
   - Connection events (connect, disconnect)
   - Text input handling
   - Audio data handling (mic_audio_data, raw_audio_data, mic_audio_end)
   - Interrupt signal
   - History management (fetch_history_list, fetch_history, clear_history)
   - Config switching
   - Log level setting
   - Desktop client events (desktop_register, desktop_live2d_action, etc.)

5. **Graceful shutdown** (lines 806-872)
   - Signal handlers
   - Resource cleanup
   - Exit handling

6. **Server entry point** (lines 878-942)
   - Config initialization
   - Uvicorn runner

### Refactoring Recommendations

#### Option A: Module Split (Recommended)

Split into focused modules:

```
src/anima/
├── socketio_server.py       # Entry point only (~50 lines)
├── server/
│   ├── __init__.py
│   ├── state.py             # Global state management (~80 lines)
│   ├── session.py           # Session factories (~200 lines)
│   ├── events/
│   │   ├── __init__.py
│   │   ├── connection.py    # connect/disconnect handlers
│   │   ├── chat.py          # text_input, audio events
│   │   ├── history.py       # history management
│   │   └── desktop.py       # desktop client events
│   ├── lifecycle.py         # startup/shutdown (~100 lines)
│   └── desktop.py           # Desktop client utilities (~100 lines)
```

**Benefits:**
- Each module has single responsibility
- Easier to test individual components
- Better code organization
- Easier to find related code

#### Option B: Class-based Refactor

Convert to class-based architecture:

```python
# server/server.py
class SocketIOServer:
    def __init__(self, config: AppConfig):
        self.config = config
        self.state = ServerState()
        self.session_manager = SessionManager()
        self.event_handlers = EventHandlerRegistry()

    async def start(self):
        await self._setup_event_handlers()
        await self._setup_signal_handlers()

    async def stop(self):
        await self.state.cleanup_all()
```

**Benefits:**
- Better encapsulation
- Easier dependency injection
- More testable

### Immediate Small Wins

Without major restructuring:

1. **Extract session management** to `server/session.py`:
   ```python
   # Move: session_contexts, orchestrators, adapters dicts
   # Move: get_or_create_context, get_or_create_orchestrator, get_or_create_adapter
   # Move: cleanup_context, cleanup_all_resources
   ```

2. **Extract desktop client logic** to `server/desktop.py`:
   ```python
   # Move: DESKTOP_CLIENT_TYPES, desktop_clients
   # Move: broadcast_to_desktop_clients
   # Move: desktop_register, desktop_live2d_action handlers
   ```

3. **Extract event handlers** to `server/events/`:
   ```python
   # Each file registers handlers with a decorator pattern
   @register_event('text_input')
   async def handle_text_input(sid, data): ...
   ```

---

## 2. orchestrator.py (571 lines)

**Location:** `src/anima/services/conversation/orchestrator.py`

### Current Responsibilities

1. **Pipeline setup** (lines 127-159)
   - Default pipeline configuration
   - Step registration

2. **Handler registration** (lines 161-229)
   - Event router management
   - Handler registration

3. **Lifecycle management** (lines 231-256)
   - Start/stop
   - Interrupt handling

4. **Input processing** (lines 258-326)
   - Text/audio input
   - Pipeline execution

5. **Conversation flow** (lines 328-462)
   - Memory retrieval
   - Agent interaction
   - Response handling

6. **Audio synthesis** (lines 464-505)
   - TTS generation
   - Event emission

7. **Event emission helpers** (lines 507-611)
   - `_emit_audio_with_expression`
   - `_emit_event`
   - `_emit_expression`
   - `_emit_expression_sync`

8. **Memory formatting** (lines 626-647)
   - Context formatting

### Refactoring Recommendations

#### Extract Audio Module

Move audio-related logic to `orchestrator/audio.py`:

```python
# orchestrator/audio.py
class AudioSynthesizer:
    def __init__(self, tts_engine, live2d_config, event_bus):
        self.tts_engine = tts_engine
        self.live2d_config = live2d_config
        self.event_bus = event_bus

    async def synthesize(self, text: str, emotions: list) -> Optional[str]:
        # _synthesize_audio logic

    async def emit_with_expression(self, audio_path, emotions, text):
        # _emit_audio_with_expression logic
```

#### Extract Memory Handler

Move memory logic to `orchestrator/memory.py`:

```python
# orchestrator/memory.py
class ConversationMemory:
    def __init__(self, memory_system, session_id):
        self.memory_system = memory_system
        self.session_id = session_id

    async def retrieve_context(self, query: str) -> str:
        # Memory retrieval logic

    async def store_turn(self, user_input, response, emotions, audio_path):
        # Store conversation turn

    def format_context(self, memories) -> str:
        # _format_memory_context logic
```

#### Extract Expression Emitter

Move expression logic to `orchestrator/expression.py`:

```python
# orchestrator/expression.py
class ExpressionEmitter:
    def __init__(self, event_bus, session_id):
        self.event_bus = event_bus
        self._seq_counter = 0

    async def emit(self, expression: str):
        # _emit_expression logic

    def emit_sync(self, expression: str):
        # _emit_expression_sync logic
```

### Recommended Structure

After refactoring:

```
services/conversation/
├── __init__.py
├── orchestrator.py       # Main orchestrator (~250 lines)
├── audio.py              # Audio synthesis (~100 lines)
├── memory.py             # Memory handling (~80 lines)
└── expression.py         # Expression emission (~60 lines)
```

---

## 3. desktop_live2d_chatter.py (506 lines)

**Location:** `src/anima/adapters/implementations/desktop_live2d_chatter.py`

### Current Responsibilities

1. **Configuration** (lines 29-43)
   - DesktopChatterConfig dataclass

2. **Adapter lifecycle** (lines 129-142)
   - Start/stop methods

3. **Output handling** (lines 144-172)
   - Event dispatching
   - Format conversion

4. **Input API** (lines 174-278)
   - send_text, send_audio, send_interrupt
   - EventBus integration

5. **Compatibility API** (lines 280-383)
   - handle_text_input, handle_audio_chunk, handle_audio_end
   - Backward compatibility layer

6. **VAD handling** (lines 385-438)
   - VAD state management
   - Speech start/end detection

7. **Output helpers** (lines 440-506)
   - _send_text_output
   - _send_audio_output
   - _send_control
   - etc.

### Analysis

This file is **well-structured** with clear separation of concerns:
- Input handling (EventBus-based)
- VAD processing
- Output formatting
- Compatibility layer

### Refactoring Recommendations

**Priority: Low** - The file is well-organized.

Minor improvements:

1. **Extract VAD mixin** (optional):
   ```python
   # adapters/mixins/vad.py
   class VADMixin:
       def _handle_vad_active(self, current_time): ...
       def _clear_vad_state(self): ...
       async def _handle_speech_start(self): ...
       async def _handle_speech_end(self, audio_data): ...
   ```

2. **Extract output formatters** (optional):
   ```python
   # adapters/formatters.py
   class OutputFormatter:
       def format_text(self, event): ...
       def format_audio(self, event): ...
       def format_control(self, event): ...
   ```

---

## 4. glm_llm.py (477 lines)

**Location:** `src/anima/services/llm/implementations/glm_llm.py`

### Current Responsibilities

1. **Initialization** (lines 30-131)
   - Client setup
   - Configuration loading
   - API key validation

2. **Message building** (lines 132-160)
   - System prompt injection
   - History management

3. **Chat methods** (lines 162-285)
   - Non-streaming chat
   - Retry logic
   - Error handling

4. **Stream chat** (lines 287-420)
   - Streaming implementation
   - Retry logic (duplicated)
   - Error handling (duplicated)

5. **Helper methods** (lines 422-477)
   - History management
   - Interrupt handling
   - Resource cleanup

### Analysis

**Main issue:** Code duplication between `chat()` and `chat_stream()`:
- Retry logic is duplicated (~70 lines each)
- Error handling is duplicated
- Logging is duplicated

### Refactoring Recommendations

#### Extract Retry Decorator

```python
# utils/retry.py
def with_retry(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                except asyncio.TimeoutError:
                    last_error = "Timeout"
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))
            raise ConnectionError(f"Failed after {max_retries} retries: {last_error}")
        return wrapper
    return decorator
```

#### Extract Logging Mixin

```python
# services/llm/mixins.py
class LoggingMixin:
    def log_call_start(self, call_id, model, input_text, history_length):
        logger.info(f"[{self.__class__.__name__}:{call_id}] Starting call...")

    def log_call_success(self, call_id, response, elapsed_time):
        logger.info(f"[{self.__class__.__name__}:{call_id}] Success in {elapsed_time:.2f}s")

    def log_call_error(self, call_id, error):
        logger.error(f"[{self.__class__.__name__}:{call_id}] Error: {error}")
```

#### Unified Stream Handler

```python
# services/llm/base.py
class BaseLLM:
    async def _execute_with_retry(self, request_func, process_func, call_id):
        """Unified retry and error handling for both stream and non-stream"""
        ...
```

### After Refactoring

```python
# glm_llm.py (~250 lines)
@ProviderRegistry.register_service("llm", "glm")
class GLMLLM(LLMInterface, LoggingMixin):
    @with_retry(max_retries=3, delay=1.0)
    async def chat(self, user_input: str, **kwargs) -> str:
        # Simplified implementation without retry logic
        ...

    @with_retry(max_retries=3, delay=1.0)
    async def chat_stream(self, user_input: str, **kwargs) -> AsyncIterator[str]:
        # Simplified implementation without retry logic
        ...
```

---

## 5. service_context.py (379 lines)

**Location:** `src/anima/service_context.py`

### Current Responsibilities

1. **Service storage** (lines 31-52)
   - ASR, TTS, LLM, VAD, Memory instances

2. **Initialization methods** (lines 69-361)
   - `load_from_config()` - Main loader
   - `load_cache()` - Cache loader
   - `init_asr()`, `init_tts()`, `init_llm()`, `init_local_llm()`, `init_vad()`, `init_memory()`

3. **Lifecycle management** (lines 367-391)
   - Resource cleanup

4. **Business flow** (lines 397-451)
   - `process_text_input()`
   - `process_audio_input()`

5. **Config switching** (lines 457-472)
   - Hot config reload

### Analysis

The file is **well-organized** but the `init_memory()` method is long (~50 lines) with configuration loading.

### Refactoring Recommendations

**Priority: Low** - The structure is acceptable.

Minor improvements:

1. **Extract memory config loading**:
   ```python
   # config/memory.py
   def load_memory_config() -> dict:
       """Load memory configuration from YAML"""
       ...
   ```

2. **Use dependency injection for config**:
   ```python
   class ServiceContext:
       def __init__(self, config_loader: ConfigLoader = None):
           self.config_loader = config_loader or DefaultConfigLoader()
   ```

---

## 6. intensity.py (418 lines)

**Location:** `src/anima/avatar/strategies/intensity.py`

### Analysis

This file is **well-structured** with:
- Single responsibility (intensity-based timeline calculation)
- Clear method separation
- Good documentation
- Proper encapsulation

### Recommendation

**No refactoring needed.** This file follows good design principles.

---

## Implementation Priority

### Phase 1: High Priority (socketio_server.py)

1. Extract `server/session.py` - Session management
2. Extract `server/desktop.py` - Desktop client utilities
3. Extract `server/lifecycle.py` - Startup/shutdown

### Phase 2: Medium Priority (orchestrator.py)

1. Extract `orchestrator/audio.py` - Audio synthesis
2. Extract `orchestrator/memory.py` - Memory handling
3. Extract `orchestrator/expression.py` - Expression emission

### Phase 3: Low Priority (Others)

1. Extract retry decorator for LLM implementations
2. Consider VAD mixin for adapters
3. Memory config extraction

---

## Testing Strategy

After refactoring, ensure:

1. **Unit tests** for each extracted module
2. **Integration tests** for module interactions
3. **Regression tests** for existing functionality
4. **Performance tests** to ensure no degradation

---

## Conclusion

The main refactoring target is `socketio_server.py` (942 lines) which has too many responsibilities. Splitting it into focused modules will significantly improve maintainability.

Other files have reasonable structure and can be improved incrementally without major restructuring.
