# SERVICES — PROVIDER IMPLEMENTATIONS

**Generated:** 2026-05-10

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW

Service implementations for LLM, ASR, TTS, VAD, and Live2D. Follows consistent provider plugin pattern: ABC interface → implementations → factory → `__init__.py` re-exports.

## STRUCTURE

```
services/
├── speech/                 # Speech processing
│   ├── asr/                # Automatic Speech Recognition
│   │   ├── interface.py    # ASRInterface ABC
│   │   ├── factory.py      # ASRFactory
│   │   ├── faster_whisper_asr.py
│   │   ├── funasr_asr.py
│   │   ├── glm_asr.py
│   │   └── mock_asr.py
│   └── tts/                # Text-to-Speech
│       ├── interface.py    # TTSInterface ABC
│       ├── factory.py      # TTSFactory
│       ├── chattts_tts.py
│       ├── edge_tts.py
│       ├── glm_tts.py
│       ├── gpt_sovits_tts.py
│       ├── kokoro_tts.py
│       ├── vibe_voice_tts.py
│       └── mock_tts.py
├── intelligence/           # AI models
│   ├── llm/                # Language Models
│   │   ├── interface.py    # LLMInterface ABC
│   │   ├── factory.py      # LLMFactory
│   │   ├── glm_llm.py
│   │   ├── openai_llm.py   # 430 lines — largest LLM provider
│   │   ├── deepseek_llm.py
│   │   ├── ollama_llm.py
│   │   └── local_lora_llm.py  # 378 lines
│   └── vad/                # Voice Activity Detection
│       ├── interface.py    # VADInterface ABC
│       ├── silero_vad.py   # 454 lines — largest service file
│       └── mock_vad.py
├── audio/                  # Audio processing pipeline
│   ├── processor.py        # AudioProcessorInterface
│   ├── vad_audio_processor.py
│   └── simple_vad_processor.py
└── live2d/                 # Live2D integration
    ├── action_queue.py     # Action scheduling
    ├── presets/            # Preset motion/expression configs
    └── viseme_sync.py      # Audio-driven viseme matching
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add LLM provider | `intelligence/llm/` | Implement `LLMInterface`, register via `@ProviderRegistry` |
| Add ASR provider | `speech/asr/` | Implement `ASRInterface` |
| Add TTS provider | `speech/tts/` | Implement `TTSInterface` |
| Add VAD provider | `intelligence/vad/` | Implement `VADInterface` |
| LLM streaming logic | `intelligence/llm/openai_llm.py` | Reference implementation — 430 lines |
| VAD processing | `intelligence/vad/silero_vad.py` | 454 lines — audio chunk processing |
| Audio pipeline | `audio/` | Pre/post-processing wrappers around VAD |
| Live2D viseme sync | `live2d/viseme_sync.py` | Phoneme → viseme mapping |

## KEY PATTERNS

- **Interface → Implementation → Factory → Re-export**: Every provider domain follows this exact pattern.
- **`@ProviderRegistry.register_service`**: Decorator-based registration (ADR-003). No if/elif chains.
- **Config + Service pairing**: Provider configs at `config/providers/{type}/` mirror implementations here.
- **Streaming**: LLM responses stream via `astream()` — never buffer full response (ADR-004).

## ANTI-PATTERNS

- ❌ Never use `if/elif` chains for provider selection — use `@ProviderRegistry`
- ❌ Never buffer full LLM response before output — stream tokens (ADR-004)
- ❌ Do not add new providers without corresponding config class at `config/providers/`

## NOTES

- `silero_vad.py` (454 lines) conflates VAD logic with audio processing — consider splitting.
- `openai_llm.py` (430 lines) has absorbed disproportionate complexity (streaming, tool calling, history).
- Mock implementations exist for all providers — use for testing and CI.
- `action_queue.py` has a TODO about client interrupt notification (line 166).
