## Why

RTX 5090D (Blackwell architecture, compute capability sm370) is incompatible with standard PyTorch CUDA builds that only support up to sm90. Users with 50-series GPUs cannot run GPT-SoVITS out of the box — they encounter `FATAL: this function is for sm80, but was built for sm370` errors. This change documents the complete setup workflow and required code patches to make GPT-SoVITS work on RTX 5090D, enabling users of the latest NVIDIA hardware to use Anima's GPT-SoVITS integration.

## What Changes

- Comprehensive setup guide for RTX 5090D users in `docs/` covering both WSL2 and native Windows approaches
- Required code patches for GPT-SoVITS (not Anima) to fix PyTorch nightly compatibility issues:
  - `Tuple` type annotation import fix in `patched_mha_with_cache.py`
  - `weights_only=False` for `torch.load()` calls
- Updated `design.md` in the `add-gpt-sovits-tts` change with 5090D-specific notes
- Verification script to confirm CUDA + PyTorch compatibility

## Capabilities

### New Capabilities
- `rtx5090-setup-guide`: Step-by-step guide for setting up GPT-SoVITS on RTX 5090D, including WSL2 environment, CUDA 12.8, PyTorch nightly, and required code patches

### Modified Capabilities
- None

## Impact

- **New file**: `docs/gpt-sovits-rtx5090-setup.md` — complete setup guide for 50-series GPU users
- **New file**: `scripts/verify_cuda_compat.py` — verification script for CUDA/PyTorch compatibility
- **Documentation update**: Cross-reference from the existing `add-gpt-sovits-tts` artifacts to the new guide
- **No Anima code changes needed**: All patches are in GPT-SoVITS codebase, not Anima
