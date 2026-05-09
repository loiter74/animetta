## Why

GPT-SoVITS api_v2.py must be started separately before Anima can use it. This creates friction — users must manually SSH into WSL2 or open a separate terminal. Integrating startup into `scripts/start.py` automates the process, making `gpt_sovits` TTS as easy to use as any other provider.

## What Changes

- Add `start_gpt_sovits()` function in `scripts/start/services.py` that launches `api_v2.py` as a subprocess
- Auto-detect GPT-SoVITS repo location or read from config
- Support conda env Python and direct Python executable
- Update `scripts/start.py` to start GPT-SoVITS when TTS provider is `gpt_sovits*`
- Add `gpt_sovits` config section in `config.yaml` (path, python, port)

## Capabilities

### New Capabilities
- `gpt-sovits-server-lifecycle`: Automatic startup and shutdown of GPT-SoVITS inference server via Anima's startup script

### Modified Capabilities
- None

## Impact

- **Modified**: `config/config.yaml` — add `system.gpt_sovits` config block
- **Modified**: `scripts/start/__init__.py` — export `start_gpt_sovits`
- **Modified**: `scripts/start/services.py` — add `start_gpt_sovits()`, `get_gpt_sovits_config()`, `_detect_gpt_sovits_path()`
- **Modified**: `scripts/start.py` — call `start_gpt_sovits()` for gpt_sovits providers
