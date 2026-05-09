## Context

Anima currently supports multiple TTS providers (Edge TTS, GLM, OpenAI, ChatTTS, Kokoro, VibeVoice) via a plugin architecture using `ProviderRegistry`. Each provider has:
1. A config class registered with `@ProviderRegistry.register("tts", "type")` 
2. A service class registered with `@ProviderRegistry.register_service("tts", "type")` implementing `TTSInterface`
3. A branch in `TTSFactory._build_config()` for config construction
4. An entry in the `TTSConfig` discriminated union type

GPT-SoVITS (RVC-Boss/GPT-SoVITS, 57k+ stars) is a powerful few-shot voice cloning TTS engine. It exposes a FastAPI REST API (`api_v2.py`) on port 9880 by default. The v2 API is cleaner and more feature-rich than the legacy v1 API.

## Goals / Non-Goals

**Goals:**
- Add `gpt_sovits` as a TTS provider option in Anima
- Connect to a separately-running GPT-SoVITS v2 API server via HTTP
- Support all essential inference parameters: reference audio, language, speed, sampling parameters
- Follow existing TTS plugin patterns exactly (ProviderRegistry, TTSInterface, TTSFactory)
- Support streaming (chunked audio) and non-streaming modes

**Non-Goals:**
- Bundling or managing the GPT-SoVITS server process (user runs it separately)
- Training/fine-tuning GPT-SoVITS models from Anima
- Replacing any existing TTS provider

## Decisions

### 1. Use GPT-SoVITS v2 API (api_v2.py) over legacy v1 API (api.py)

**Decision:** Target the v2 API at `/tts` endpoint.

**Rationale:**
- v2 API (`api_v2.py`) uses a cleaner TTS config file (`tts_infer.yaml`) and has a well-defined `TTS_Request` model
- Parameters are more comprehensive (speed_factor, fragment_interval, batch_size, streaming_mode)
- The `TTS_Request` Pydantic model makes integration self-documenting
- v1 API is less maintained going forward

**Alternative considered:** Using the legacy v1 `api.py` — simpler but less feature-rich, no streaming mode.

### 2. HTTP REST API approach (remote mode) — like VibeVoice

**Decision:** Connect to GPT-SoVITS via HTTP using `httpx.AsyncClient`, same pattern as VibeVoice. The user runs `api_v2.py` separately.

**Rationale:**
- GPT-SoVITS is a heavy dependency (PyTorch, CUDA, multiple GB of models) — bundling it would complicate Anima's dependency footprint significantly
- The REST API pattern is already proven in Anima with VibeVoice
- Users can run the GPT-SoVITS server on the same machine or a separate GPU server
- The server can be started/stopped independently without affecting Anima

**Alternative considered:** Direct Python import — would require GPT-SoVITS as a hard dependency, doubling Anima's install size. Not practical.

### 3. Use `httpx` for async HTTP calls

**Decision:** Use `httpx.AsyncClient` for HTTP requests to GPT-SoVITS.

**Rationale:**
- `httpx` is likely already in the project's dependencies (used elsewhere)
- Async compatibility with Anima's async graph nodes
- Supports streaming responses (for future streaming TTS support)
- Timeout and retry configuration

### 4. Default reference audio via config

**Decision:** Require `ref_audio_path`, `prompt_text`, `prompt_lang`, and `text_lang` in configuration. The user must provide at least a reference audio file and its transcript.

**Rationale:**
- GPT-SoVITS always requires a reference audio for voice cloning — without it, inference fails
- These are mandatory parameters in the GPT-SoVITS API
- Users can change reference audio at runtime by modifying the config (or via a future API)

**Alternative considered:** Making ref_audio optional and falling back to a default — GPT-SoVITS's v2 API requires `ref_audio_path` as mandatory.

## Architecture

### Data flow

```
[Anima TTS Node]
    → tts_engine.synthesize(text)
        → GPTSoVITSTTS._call_api(text, params)
            → httpx.AsyncClient.post("http://host:port/tts", json=payload)
                → GPT-SoVITS api_v2.py (separate process)
                    → generates WAV audio
                    ← returns WAV audio stream
            ← audio bytes
    ← audio bytes / file path
```

### Files to Create/Modify

**New files:**
- `src/anima/config/providers/tts/gpt_sovits.py` — config class
- `src/anima/services/speech/tts/gpt_sovits_tts.py` — service implementation

**Modified files:**
- `src/anima/config/providers/tts/__init__.py` — add to TTSConfig union
- `src/anima/services/speech/tts/factory.py` — add provider branch
- `config/services.yaml` — add gpt_sovits config entry

## Risks / Trade-offs

- **GPT-SoVITS server must be running separately** → Document setup steps clearly; user follows GPT-SoVITS install guide
- **Heavy GPU requirements** → GPT-SoVITS requires ~4-8GB VRAM; users without GPU can run CPU mode (slower)
- **Reference audio dependency** → Voice cloning always needs a reference; quality depends on the reference audio chosen
- **Port conflict** → Default port 9880 may conflict; make port configurable
- **No streaming support in initial version** → GPT-SoVITS v2 supports streaming but the current TTSInterface returns complete audio; streaming can be added later

## Known GPT-SoVITS Bugs

The following issues are in GPT-SoVITS itself and may affect users of this integration:

| Bug | Symptom | Scope | Workaround |
|-----|---------|-------|------------|
| **RTX 50系显卡不兼容** | `FATAL: this function is for sm80, but was built for sm370` 或 `sm_120 is not compatible` | RTX 5090D (sm_120 / Blackwell) 需 cu128+ PyTorch 支持 | 参考 [docs/gpt-sovits-rtx5090-setup.md](../../docs/gpt-sovits-rtx5090-setup.md) — 完整部署指南 |
| **V2 并行推理输出为空** | 推理成功但返回空音频 | GPT-SoVITS V2 模型在 `parallel_infer=true` 时有 bug | 在 `services.yaml` 中将 `text_split_method` 设为非切分模式，或使用 V2Pro/V3/V4 模型 |
| **api_v2.py 直调质量不佳** | 相比 webui 有杂波/噪音 | 偶发性问题，与模型版本及参考音频质量有关 | 先用 webui 验证参考音频和模型效果，再切到 API 模式 |
| **`connected errored out`** | WebUI 连接报错 | 通常是因为关闭了启动 cmd 窗口 | 保持 api_v2.py 进程后台常驻，不要关闭终端 |
