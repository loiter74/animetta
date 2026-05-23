# Training Paradigm — Character Singing Voice Model

## Quick Start (for a new character)

```bash
# 1. Edit config.yaml (change character name)
# 2. Place raw audio files in data/training/raw/
# 3. Run preprocessing pipeline
python scripts/train/02_slice_and_denoise.py
python scripts/train/03_normalize.py
python scripts/train/04_augment_pitch.py
python scripts/train/05_split_dataset.py
# 4. Open RVC WebUI → train with resulting dataset
#    Experiment name: {character.name}
#    Sample rate: {rvc.sample_rate}
#    Version: {rvc.version}
# 5. Deploy to Anima
python scripts/train/deploy_to_anima.py
```

## Data Requirements

- Total: 30-60 minutes clean vocals
- Singing data: at least 10 minutes (critical)
- Format: WAV, any sample rate (will be resampled)
- No background music, no reverb

## Directory Layout

```
data/training/
├── raw/              # Raw input — place files here
├── processed/        # After slicing + denoising
├── augmented/        # After pitch augmentation
└── ready/            # Final dataset for RVC WebUI
```
