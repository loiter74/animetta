## Context

Anima's `scripts/start.py` already manages service lifecycle for backend, frontend, web config, and VibeVoice TTS server. GPT-SoVITS needs similar integration.

## Auto-Detection Strategy

1. Check `config.yaml` → `system.gpt_sovits.path` (explicit config)
2. If empty, scan `../GPT-SoVITS/`, `~/GPT-SoVITS/`, `E:/GPT-SoVITS/` for `api_v2.py`
3. If not found, warn user

For Python interpreter:
1. Check `config.yaml` → `system.gpt_sovits.python` (explicit)
2. Try common conda env paths: `miniconda3/envs/gpt-sovits/`
3. Fallback to `conda run -n gpt-sovits`
4. If all fail, warn user

## Startup Flow

```python
start.py → get_tts_provider() → "gpt_sovits_evil"
  → start_gpt_sovits()
    → detect repo path
    → detect python
    → subprocess.Popen(["python", "api_v2.py", "-a", "127.0.0.1", "-p", "9880", "-c", "tts_infer.yaml"])
    → 5s delay for model loading
  → start_backend()  # Anima starts after TTS server
```

## Decisions

### Config-driven rather than environment variables
System-level config in config.yaml keeps everything in one place and is self-documenting.

### Conda env auto-detection
Most users install GPT-SoVITS in a conda env named `gpt-sovits`. Auto-detecting this avoids manual config.

### 5-second startup delay
GPT-SoVITS loads ~200MB of models on startup. 5s is a safe buffer before Anima tries to connect.
