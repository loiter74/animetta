## Why

GPT-SoVITS is a state-of-the-art open-source few-shot voice cloning TTS engine (57k+ GitHub stars) that can generate natural speech with just 1 minute of reference audio. Adding it as a TTS provider gives Anima users access to high-quality voice cloning capabilities — allowing AI characters to speak in custom voices with emotional expression, support for Chinese/English/Japanese/Korean/Cantonese, and local inference without API costs.

## What Changes

- New TTS provider: `gpt_sovits` connecting to a locally running GPT-SoVITS inference server via REST API
- Config class + service class following existing TTS plugin pattern (ProviderRegistry)
- Configuration in `services.yaml` for GPT-SoVITS server address, reference audio, and inference parameters
- Documentation for setting up the GPT-SoVITS server separately

## Capabilities

### New Capabilities
- `gpt-sovits-tts`: GPT-SoVITS TTS integration as an Anima TTS provider, supporting remote API inference with configurable reference audio, language, and voice parameters

### Modified Capabilities
- None (no spec-level behavior changes to existing capabilities)

## Impact

- **New files**: `src/anima/config/providers/tts/gpt_sovits.py` (config), `src/anima/services/speech/tts/gpt_sovits_tts.py` (service)
- **Modified files**: `src/anima/services/speech/tts/factory.py` (new provider branch), `src/anima/config/providers/tts/__init__.py` (add to union type), `config/services.yaml` (add config entry)
- **External dependency**: Requires a running GPT-SoVITS `api_v2.py` server process (managed by the user, not bundled)
- **Python dependency**: `httpx` for async HTTP calls (likely already present)
