# SERVICES — PROVIDER IMPLEMENTATIONS

**Generated:** 2026-05-23

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW

Service implementations for LLM, ASR, TTS, VAD, singing (RVC/SVC), live (Bilibili danmaku), and meme processing. Follows consistent provider plugin pattern: ABC interface -> implementations -> factory -> `__init__.py` re-exports.

## STRUCTURE

```
services/
├── speech/                 # Speech processing
│   ├── asr/                # ASR (4 providers: faster_whisper, funasr, glm, mock)
│   └── tts/                # Text-to-Speech — core/contrib layered
│       ├── interface.py    # TTSInterface ABC
│       ├── factory.py      # TTSFactory
│       ├── mock_tts.py     # Testing stub
│       ├── edge_tts.py     # core: active — zero-dep
│       ├── qwen3_tts.py    # core: active — default
│       ├── gpt_sovits_tts.py # core: active — local
│       └── contrib/        # maintained / experimental
│           ├── glm_tts.py
│           ├── kokoro_tts.py
│           ├── vibe_voice_tts.py
│           ├── chattts_tts.py
│           └── glados_effect.py
├── intelligence/           # AI models
│   ├── llm/                # LLM (5 providers: glm, openai, deepseek, ollama, local_lora)
│   └── vad/                # VAD (silero, mock)
├── audio/                  # Audio pipeline (processor + VAD wrappers)
├── live2d/                 # Live2D action queue + viseme sync
├── singing/                # RVC/SVC song synthesis pipeline
│   ├── interface.py        # SingingInterface ABC
│   ├── svc_pipeline.py     # RVC/SVC chain orchestrator
│   ├── rvc_bridge.py       # RVC voice conversion
│   ├── svc_bridge.py       # SVC voice conversion
│   ├── mixer.py            # Audio mixing
│   ├── separator.py        # Source separation (Demucs)
│   ├── lyrics.py           # Lyric alignment / synthesis
│   └── bilibili.py         # Bilibili song ID integration
├── live/                   # Bilibili livestream
│   └── bilibili_danmaku.py # WebSocket danmaku listener + AI reply
└── meme/                   # Meme pattern detection
    ├── analyzer.py         # Meme matching logic
    ├── bilibili_collector.py
    ├── bilibili_interaction.py
    └── danmaku_buffer.py   # Context buffer for meme detection
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add LLM provider | `intelligence/llm/` | Implement `LLMInterface`, use `@ProviderRegistry` |
| Add ASR provider | `speech/asr/` | Implement `ASRInterface` |
| Add TTS provider | `speech/tts/` | Core at top level, contrib/ for experimental |
| Add VAD provider | `intelligence/vad/` | Implement `VADInterface` |
| Singing pipeline | `singing/` | `svc_pipeline.py` orchestrates RVC -> SVC chain |
| Bilibili danmaku | `live/bilibili_danmaku.py` | Listener + AI reply loop |
| LLM streaming | `intelligence/llm/openai_llm.py` | Reference — 430 lines |
| VAD processing | `intelligence/vad/silero_vad.py` | 454 lines — audio chunk processor |
| Audio pipeline | `audio/` | Pre/post-processing wrappers |
| Live2D viseme sync | `live2d/viseme_sync.py` | Phoneme -> viseme mapping |

## KEY PATTERNS

- **Interface -> Implementation -> Factory -> Re-export**: Every provider domain follows this exact pattern.
- **`@ProviderRegistry.register_service`**: Decorator-based registration (ADR-003). No if/elif chains.
- **Config + Service pairing**: Provider configs at `config/providers/{type}/` mirror implementations here.
- **Streaming**: LLM responses stream via `astream()` — never buffer full response (ADR-004).

## ANTI-PATTERNS

- ❌ Never use `if/elif` chains for provider selection — use `@ProviderRegistry`
- ❌ Never buffer full LLM response before output — stream tokens (ADR-004)
- ❌ Do not add new providers without corresponding config class at `config/providers/`

## NOTES

- `silero_vad.py` (454 lines) conflates VAD logic with audio processing — consider splitting.
- `openai_llm.py` (430 lines) has disproportionate complexity (streaming, tool calling, history).
- TTS has 9 providers: 3 core (top-level, active) + 5 contrib + 1 mock. See governance report.
- Mock implementations exist for all core provider types — use for testing and CI.
- `action_queue.py` has a TODO about client interrupt notification (line 166).
