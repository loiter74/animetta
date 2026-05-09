## ADDED Requirements

### Requirement: Miniconda installation

The system SHALL install Miniconda to the user's home directory for managing Python environments.

#### Scenario: Miniconda installed

- **WHEN** the setup script runs
- **THEN** Miniconda SHALL be installed at `~/miniconda3`
- **THEN** `conda` SHALL be available in the shell PATH

### Requirement: GPT-SoVITS conda environment

The system SHALL have a `gpt-sovits` conda environment with the correct dependencies for RTX 5090D.

#### Scenario: Environment created

- **WHEN** the gpt-sovits environment is set up
- **THEN** Python 3.10 SHALL be installed
- **THEN** PyTorch cu128 SHALL be installed with sm_120 support
- **THEN** GPT-SoVITS requirements SHALL be installed

#### Scenario: Evil model weights configured

- **WHEN** the environment is ready
- **THEN** `tts_infer.yaml` SHALL point to Evil V2 weights at `E:/BaiduNetdiskDownload/Model/Evil/Evil-V2/`
- **THEN** The GPT-SoVITS API server SHALL start on port 9880

### Requirement: Anima conda environment

The system SHALL have an `anima` conda environment for the Anima project.

#### Scenario: Environment created

- **WHEN** the anima environment is set up
- **THEN** Python 3.13 SHALL be installed
- **THEN** all Anima requirements from requirements.txt SHALL be installed

#### Scenario: Startup script detects conda

- **WHEN** `scripts/start.py` runs
- **THEN** it SHALL detect the `gpt-sovits` conda environment
- **THEN** `start_gpt_sovits()` SHALL start api_v2.py using the conda Python
