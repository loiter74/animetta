# Anima Utility Scripts

Development and training utilities for the Anima VTuber project.

## Scripts

| Script | Purpose |
|--------|---------|
| `bench.py` | LangGraph pipeline performance benchmark (1024 lines) |
| `collect-voice.py` | Download & prepare voice training data (yt-dlp + Demucs) |
| `download-models.sh` | Pre-download AI models (Kokoro, Qwen3, Whisper) |
| `process-icons.py` | Icon asset processing — white background removal + resize |
| `seed-persona.py` | Generate seed data for a persona in the memory DB |
| `start-mc-bot.py` / `.bat` | Persistent Minecraft bot launcher |

## Training Pipeline

```
train/
├── cli.py              ← Main entry: python -m scripts.train.cli --character <name>
├── config.yaml          ← Training configuration
├── collect-data.py      ← Stage 1: collect voice samples
├── prepare-data.py      ← Stage 2: preprocess audio
└── deploy.py            ← Stage 3: deploy model to Anima config
```

Usage:
```bash
# Full training pipeline
python -m scripts.train.cli --character shige_utage

# Dry run (check config)
python -m scripts.train.cli --character shige_utage --dry-run

# Deploy only
python -m scripts.train.cli --character shige_utage --deploy-only
```
