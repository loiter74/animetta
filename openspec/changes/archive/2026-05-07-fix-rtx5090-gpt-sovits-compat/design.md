## Context

RTX 5090D uses NVIDIA's Blackwell architecture with compute capability **sm370**. Standard PyTorch wheels (CUDA 12.4/12.6) are compiled for sm37-sm90 only. Additionally, GPT-SoVITS has compatibility issues with PyTorch nightly (required for sm370 support).

Two approaches exist:
1. **WSL2 (recommended)**: Run GPT-SoVITS in WSL2 Ubuntu with CUDA 12.8 + PyTorch nightly
2. **Native Windows**: Direct Windows setup with PyTorch nightly (may have additional dll/torio issues)

## Goals / Non-Goals

**Goals:**
- Document step-by-step setup for GPT-SoVITS on RTX 5090D
- Provide the exact code patches needed for GPT-SoVITS compatibility with PyTorch nightly
- Verify CUDA/PyTorch compatibility with a verification script
- Enable Anima GPT-SoVITS integration on 5090D hardware

**Non-Goals:**
- Modifying Anima's codebase (all patches target GPT-SoVITS files)
- Supporting older GPU architectures (these don't need special setup)
- Bundling GPT-SoVITS with Anima

## Decisions

### 1. WSL2 as the primary recommended approach

**Decision:** Primary documentation targets WSL2 (Ubuntu) setup.

**Rationale:**
- Issue #2026 confirms WSL2 works reliably with RTX 5080/5090
- Native Windows PyTorch nightly has torio/FFmpeg extension issues (issue #2192)
- WSL2 provides a Linux environment that most AI tools are developed and tested on
- Better filesystem performance for model I/O compared to native Windows

**Alternative:** Native Windows — possible but more fragile.

### 2. Separate setup guide document

**Decision:** Create `docs/gpt-sovits-rtx5090-setup.md` as a standalone guide.

**Rationale:**
- The setup involves modifying GPT-SoVITS files, not Anima files
- Users need a reference they can follow independently
- Cross-reference from existing Anima GPT-SoVITS integration docs

## Setup Architecture

### WSL2 Solution

```
Windows 11 + NVIDIA Driver (CUDA 12.8 capable)
    └── WSL2 (Ubuntu 22.04/24.04)
        └── Conda env (Python 3.10)
            ├── PyTorch nightly (CUDA 12.8)  ← sm370 support
            ├── GPT-SoVITS repo
            │   ├── Patch: Tuple import fix
            │   └── Patch: weights_only=False
            └── api_v2.py --port 9880
                    │
                    ▼
            Anima (connects via HTTP)
```

### Required Code Patches

#### Patch 1: Tuple type annotation (patched_mha_with_cache.py)
```python
# GPT_SoVITS/AR/modules/patched_mha_with_cache.py
# Add at top of file:
from typing import Tuple
```

#### Patch 2: weights_only for torch.load (inference_webui.py, api.py, api_v2.py, etc.)
```python
# Change all torch.load(model_path, map_location=...) calls to:
torch.load(model_path, map_location=..., weights_only=False)
```

## Risks / Trade-offs

- **PyTorch nightly stability** → Nightly builds may have regressions; pin to a known working nightly version
- **weights_only=False security** → Only load model files from trusted sources (your own training)
- **WSL2 performance overhead** → GPU passthrough in WSL2 is near-native for compute, but filesystem I/O on /mnt/ is slow
- **CUDA 12.8 driver requirement** → Must update to latest NVIDIA Game Ready/Studio driver that supports CUDA 12.8 on WSL2
