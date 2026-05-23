#!/usr/bin/env python3
"""Split augmented dataset into train/validation sets.

Input:  data/training/augmented/*.wav (or processed/ if no augmented)
Output: data/training/ready/train/ and data/training/ready/val/
"""
import random
import shutil
from pathlib import Path

import yaml
from loguru import logger


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    augmented_dir = Path(config["data"]["augmented_dir"])
    processed_dir = Path(config["data"]["processed_dir"])

    # Determine source: prefer augmented, fallback to processed
    if augmented_dir.exists() and any(augmented_dir.iterdir()):
        source_dir = augmented_dir
        logger.info(f"Using augmented data from: {source_dir}")
    else:
        source_dir = processed_dir
        logger.info(f"Using processed data from: {source_dir}")

    # Output: data/training/ready/
    ready_dir = Path(config["data"]["processed_dir"]).parent / "ready"
    train_dir = ready_dir / "train"
    val_dir = ready_dir / "val"
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    wavs = list(source_dir.glob("*.wav"))
    if not wavs:
        logger.warning(f"No WAV files in {source_dir}")
        return

    # Shuffle deterministically for reproducibility
    random.Random(42).shuffle(wavs)
    split_idx = int(len(wavs) * 0.9)
    train_files = wavs[:split_idx]
    val_files = wavs[split_idx:]

    for fpath in train_files:
        shutil.copy2(str(fpath), str(train_dir / fpath.name))

    for fpath in val_files:
        shutil.copy2(str(fpath), str(val_dir / fpath.name))

    logger.info(f"Train: {len(train_files)} files")
    logger.info(f"Val:   {len(val_files)} files")
    logger.info(f"Ready dataset at: {ready_dir}")
    logger.info(f"Total: {len(wavs)} files")


if __name__ == "__main__":
    main()
