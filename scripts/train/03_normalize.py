#!/usr/bin/env python3
"""Normalize audio: resample to target SR, loudness normalize.

Input:  data/training/processed/*.wav
Output: data/training/processed/*.wav (in-place)
"""
import argparse
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
import yaml
from loguru import logger


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_audio(input_path: Path, output_path: Path,
                    target_sr: int, target_loudness: float) -> float:
    """Resample to target SR, measure and normalize loudness."""
    audio, orig_sr = librosa.load(str(input_path), sr=None, mono=True)

    # Resample
    if orig_sr != target_sr:
        audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)

    # Measure loudness
    meter = pyln.Meter(target_sr)
    loudness = meter.integrated_loudness(audio)

    # Normalize
    audio_normalized = pyln.normalize.loudness(audio, loudness, target_loudness)

    # Peak normalize to prevent clipping
    peak = np.max(np.abs(audio_normalized))
    if peak > 0.99:
        audio_normalized = audio_normalized * (0.99 / peak)

    sf.write(str(output_path), audio_normalized, target_sr)
    return float(librosa.get_duration(y=audio_normalized, sr=target_sr))


def main():
    config = load_config()
    processed_dir = Path(config["data"]["processed_dir"])
    target_sr = config["audio"]["target_sr"]
    target_loudness = config["audio"]["target_loudness"]

    wavs = list(processed_dir.glob("*.wav"))
    if not wavs:
        logger.warning(f"No WAV files in {processed_dir}")
        return

    total_duration = 0.0
    for wav in wavs:
        try:
            dur = normalize_audio(wav, wav, target_sr, target_loudness)
            total_duration += dur
            logger.debug(f"  {wav.name}: {dur:.1f}s")
        except Exception as e:
            logger.error(f"Failed: {wav}: {e}")

    logger.info(f"Done. {len(wavs)} files, {total_duration:.1f}s total")


if __name__ == "__main__":
    main()
