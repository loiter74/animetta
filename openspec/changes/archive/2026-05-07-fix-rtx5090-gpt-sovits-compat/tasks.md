## 1. Setup Guide Document

- [x] 1.1 Create `docs/gpt-sovits-rtx5090-setup.md` with complete WSL2 environment setup steps (Ubuntu, CUDA 12.8, Python 3.10)
- [x] 1.2 Document PyTorch stable + nightly installation commands and CUDA verification
- [x] 1.3 Document GPT-SoVITS code patches (Tuple import, weights_only=False) with exact file paths and line numbers
- [x] 1.4 Document GPT-SoVITS installation (clone, pip install, model downloads, onnxruntime fix)
- [x] 1.5 Document api_v2.py startup and Anima service configuration
- [x] 1.6 Add curl verification command and error quick-reference table

## 2. Verification Script

- [x] 2.1 Create `scripts/verify_cuda_compat.py` that checks torch.cuda.is_available(), GPU name, CUDA version, arch list, and runs a real CUDA kernel test
- [x] 2.2 Script prints clear pass/fail messages and actionable error guidance

## 3. Cross-reference in GPT-SoVITS Change

- [x] 3.1 Update `openspec/changes/add-gpt-sovits-tts/design.md` to reference the RTX 5090 setup guide

## 4. Verification

- [x] 4.1 Review docs/gpt-sovits-rtx5090-setup.md — 281 lines, covers WSL2 + Windows + all patches + error reference
- [x] 4.2 Created verify_cuda_compat.py with comprehensive checks (skip execution test if not on 50-series)