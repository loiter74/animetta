## Why

The project currently has fragmented Python environment management:
- **Anima**: `.venv` using Microsoft Store Python 3.13
- **GPT-SoVITS**: Broken `.venv` pointing to deleted conda env, no base Python 3.10 available
- **5090D GPU**: Requires cu128 PyTorch across environments

Unifying under miniconda provides a single tool to manage multiple isolated Python environments with different versions and CUDA configurations.

## What Changes

- Install Miniconda (user-local, no admin needed)
- Create `anima` conda env (Python 3.13) — replaces existing `.venv`
- Create `gpt-sovits` conda env (Python 3.10, cu128 PyTorch) — for 5090D
- Migrate Anima's `.venv` to conda, update startup scripts to detect conda envs
- Configure GPT-SoVITS path in Anima config

## Capabilities

### New Capabilities
- `conda-environment-setup`: Miniconda installation + two conda environments for Anima and GPT-SoVITS

### Modified Capabilities
- None

## Impact

- **Installed**: Miniconda at `~/miniconda3`
- **New env**: `anima` (Python 3.13 + all Anima deps)
- **New env**: `gpt-sovits` (Python 3.10 + cu128 PyTorch + GPT-SoVITS deps + Evil model)
- **Modified**: `config.yaml` — set `system.gpt_sovits.path`
- **Modified**: `GPT_SoVITS/configs/tts_infer.yaml` — set Evil model weights
