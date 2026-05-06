## 1. Config Layer — KokoroTTSConfig

- [x] 1.1 Create `src/anima/config/providers/tts/kokoro.py`: `KokoroTTSConfig` class with `type: Literal["kokoro"]`, `voice`, `model_path`, `device`, `speed`, `glados_effect` (dict with enabled/pitch/stretch/overdrive/chorus/bandpass/compand/gain params)
- [x] 1.2 Update `src/anima/config/providers/tts/__init__.py`: import `KokoroTTSConfig` and add to `TTSConfig` discriminated union

## 2. Service Layer — KokoroTTS

- [x] 2.1 Create `src/anima/services/speech/tts/kokoro_tts.py`: `KokoroTTS(TTSInterface)` with:
  - Lazy model loading (`KPipeline` on first `synthesize()` call)
  - `from_config()` classmethod supporting `KokoroTTSConfig`
  - `synthesize()` returning WAV bytes via Kokoro inference
  - Optional GLaDOS effects integration via `GladosEffectProcessor`
  - `close()` for cleanup

## 3. Effect Pipeline — GladosEffectProcessor

- [x] 3.1 Create `src/anima/services/speech/tts/glados_effect.py`: `GladosEffectProcessor` class with:
  - SoX availability check on init via `torchaudio.sox_effects.apply_effects_tensor`
  - `async process(audio_bytes) -> bytes` using `torchaudio.sox_effects`
  - Default effect chain: pitch → stretch → overdrive → chorus → bandpass → compand → gain
  - Configurable effect parameters from dict
  - Graceful fallback to raw audio on error or missing SoX

## 4. Factory Registration

- [x] 4.1 Update `src/anima/services/speech/tts/factory.py`: add `kokoro` branch in `_build_config()` returning `KokoroTTSConfig`
- [x] 4.2 Update `src/anima/services/speech/tts/__init__.py`: export `KokoroTTS`, `GladosEffectProcessor`

## 5. Configuration

- [x] 5.1 Add `kokoro_glados` preset to `config/services.yaml` under `tts:` section with `type: kokoro`, voice selection, and `glados_effect` parameters
- [x] 5.2 Kokoro auto-downloads model from HuggingFace via `hf_hub_download` to `~/.cache/huggingface/hub/`. Set `HF_HOME` env var to customize cache location.

## 6. Dependencies & Testing

- [x] 6.1 Add `kokoro>=0.9.4` to `requirements.txt` (torch/torchaudio already present)
- [x] 6.2 Run basic verification: `pip install kokoro` (v0.7.16) + `misaki[zh]` + deps installed. Kokoro KPipeline with `lang_code='z'` generates audio tensor shape [58200] for "你好世界". Note: `kokoro>=0.9.4` in requirements.txt may need adjusting for Python 3.13 compatibility (spacy/thinc build issues).
- [x] 6.3 Python syntax validation passed via `ast.parse()` on all 6 files (basedpyright LSP not available on this machine)
