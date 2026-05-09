## 1. Configuration

- [x] 1.1 Add `system.gpt_sovits` config block to `config/config.yaml` (path, python, port)

## 2. Service Startup Function

- [x] 2.1 Add `get_gpt_sovits_config()` to `scripts/start/services.py` — reads config from yaml
- [x] 2.2 Add `_detect_gpt_sovits_path()` — auto-detect GPT-SoVITS repo location
- [x] 2.3 Add `_find_gpt_sovits_python()` — find conda env python
- [x] 2.4 Add `start_gpt_sovits()` — launch api_v2.py as subprocess with repo path detection and conda python

## 3. Integration

- [x] 3.1 Update `scripts/start/__init__.py` — export `start_gpt_sovits` and `get_gpt_sovits_config`
- [x] 3.2 Update `scripts/start.py` — import `start_gpt_sovits`, add gpt_sovits branch in TTS server startup logic

## 4. Verification

- [x] 4.1 All Python files compile clean
- [x] 4.2 All imports resolve correctly
- [x] 4.3 YAML config files validate
