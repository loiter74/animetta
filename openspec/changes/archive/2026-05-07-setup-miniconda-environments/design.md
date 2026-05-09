## Context

Current state:
- Anima uses `.venv` with Microsoft Store Python 3.13
- GPT-SoVITS has broken `.venv`, no working Python 3.10 installation
- 5090D needs cu128 PyTorch for Blackwell support

## Environment Architecture

```
Miniconda (~/miniconda3)
├── envs/
│   ├── anima/           ← Python 3.13
│   │   ├── torch (cpu)  ← for memory system (torchcodec)
│   │   ├── edge-tts
│   │   ├── fastapi, uvicorn, socket.io
│   │   └── ...all Anima deps
│   │
│   └── gpt-sovits/      ← Python 3.10
│       ├── torch (cu128) ← for 5090D inference
│       ├── onnxruntime-gpu==1.22.0
│       ├── GPT-SoVITS deps
│       └── Evil model weights (ref from E:\)
│
└── ...anima start.py detects conda envs automatically
```

## Installation Plan

### Step 1: Install Miniconda
Download Windows installer, install to `~/miniconda3`, add to PATH.

### Step 2: Create `gpt-sovits` environment
```bash
conda create -n gpt-sovits python=3.10 -y
conda activate gpt-sovits
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### Step 3: Create `anima` environment
```bash
conda create -n anima python=3.13 -y
conda activate anima
pip install -r requirements.txt
```

### Step 4: Configure paths
- `config.yaml` → `system.gpt_sovits.path = "C:/Users/30262/GPT-SoVITS-v2pro-20250604"`
- `tts_infer.yaml` → point to Evil V2 weights
- Copy ref audio to `config/gpt_sovits/evil/` (already done)

## Why Two Envs Instead of One

GPT-SoVITS requires Python 3.10 + cu128 PyTorch. Anima uses Python 3.13. These are incompatible, so separate environments are necessary. The `start_gpt_sovits()` function already handles this by calling the conda env's Python.
