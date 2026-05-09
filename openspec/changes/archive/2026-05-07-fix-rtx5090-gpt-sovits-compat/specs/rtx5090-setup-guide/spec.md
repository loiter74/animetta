## ADDED Requirements

### Requirement: Setup guide for RTX 5090D

The system SHALL provide a setup guide at `docs/gpt-sovits-rtx5090-setup.md` that documents the complete process for running GPT-SoVITS (and by extension Anima's GPT-SoVITS integration) on NVIDIA RTX 50-series GPUs.

#### Scenario: WSL2 environment setup

- **WHEN** a user follows the guide on Windows 11 with an RTX 5090D
- **THEN** the guide SHALL specify WSL2 Ubuntu 22.04/24.04 as the recommended environment
- **THEN** the guide SHALL include the exact commands to install CUDA 12.8 support in WSL2
- **THEN** the guide SHALL include the exact commands to create a Python 3.10 conda environment

#### Scenario: PyTorch nightly installation

- **WHEN** the user reaches the PyTorch installation step
- **THEN** the guide SHALL specify `pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128`
- **THEN** the guide SHALL include a CUDA verification step: `python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"`

#### Scenario: GPT-SoVITS code patches

- **WHEN** the user has cloned GPT-SoVITS and installed dependencies
- **THEN** the guide SHALL document the `from typing import Tuple` patch for `GPT_SoVITS/AR/modules/patched_mha_with_cache.py`
- **THEN** the guide SHALL document the `weights_only=False` change for all `torch.load()` calls
- **THEN** each patch SHALL include the exact file path and line numbers

#### Scenario: api_v2.py startup

- **WHEN** the user has patched the code and downloaded pretrained models
- **THEN** the guide SHALL include the command to start `api_v2.py`
- **THEN** the guide SHALL include steps to configure Anima's `services.yaml` for `tts: gpt_sovits`

#### Scenario: Verification of full pipeline

- **WHEN** the user has completed all setup steps
- **THEN** the guide SHALL include a verification step that sends a test TTS request via curl
- **THEN** the guide SHALL include steps to check Anima logs for successful TTS initialization
