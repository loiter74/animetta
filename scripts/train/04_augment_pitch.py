#!/usr/bin/env python3
"""Pitch augmentation using WORLD vocoder — 核心高音增强模块.

For each input clip, generates N copies at different pitch shifts:
- 0 semitones (original — always kept)
- +2 semitones (brighter, extends high range)
- -2 semitones (darker, improves generalization)
- +4 semitones (only for clips with estimated pitch < threshold Hz)

Input:  data/training/processed/*.wav
Output: data/training/augmented/*_shift{+,-}N.wav

This uses WORLD vocoder which preserves spectral envelope (formants)
while changing pitch — unlike simple resampling which changes both
pitch and timbre. This is critical for anime character voice preservation.
"""
import argparse
from pathlib import Path

import librosa
import numpy as np
import pyworld as pw
import soundfile as sf
import yaml
from loguru import logger


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def estimate_median_pitch(audio: np.ndarray, sr: int) -> float:
    """Estimate the median pitch of a clip using WORLD."""
    f0, _ = pw.dio(audio.astype(np.float64), sr)
    f0 = f0[f0 > 0]  # Remove unvoiced frames
    if len(f0) == 0:
        return 0.0
    return float(np.median(f0))


def pitch_shift_world(audio: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    """Shift pitch using WORLD vocoder (preserves spectral envelope).

    This preserves formants while changing pitch — unlike simple resampling,
    which changes both pitch and timbre.
    """
    # WORLD analysis
    f0, t = pw.harvest(audio.astype(np.float64), sr)
    f0 = pw.stonemask(audio.astype(np.float64), f0, t, sr)
    sp = pw.cheaptrick(audio.astype(np.float64), f0, t, sr)
    ap = pw.d4c(audio.astype(np.float64), f0, t, sr)

    # Shift F0
    f0_shifted = f0.copy()
    mask = f0 > 0
    f0_shifted[mask] = f0[mask] * (2 ** (semitones / 12))

    # Synthesize
    shifted = pw.synthesize(f0_shifted, sp, ap, sr)
    return shifted.astype(np.float32)


def main():
    config = load_config()
    processed_dir = Path(config["data"]["processed_dir"])
    augmented_dir = Path(config["data"]["augmented_dir"])
    augmented_dir.mkdir(parents=True, exist_ok=True)

    shifts = config["augmentation"]["pitch_shifts"]  # [0, -2, +2]
    low_shift = config["augmentation"]["extend_low_shift"]  # +4
    low_threshold = config["augmentation"]["low_pitch_threshold"]  # 400 Hz

    wavs = sorted(processed_dir.glob("*.wav"))
    if not wavs:
        logger.warning(f"No WAV files in {processed_dir}")
        return

    total_outputs = 0
    for wav in wavs:
        try:
            audio, sr = librosa.load(str(wav), sr=None, mono=True)
            median_pitch = estimate_median_pitch(audio, sr)
            logger.debug(f"  {wav.name}: median pitch = {median_pitch:.0f} Hz")

            for shift in shifts:
                output_path = augmented_dir / f"{wav.stem}_shift{shift:+d}.wav"
                if shift == 0:
                    # Original — just copy
                    sf.write(str(output_path), audio, sr)
                else:
                    shifted = pitch_shift_world(audio, sr, float(shift))
                    sf.write(str(output_path), shifted, sr)
                total_outputs += 1

            # Extra up-shift for low-pitch clips
            if 0 < median_pitch < low_threshold:
                output_path = augmented_dir / f"{wav.stem}_shift+{low_shift}.wav"
                shifted = pitch_shift_world(audio, sr, float(low_shift))
                sf.write(str(output_path), shifted, sr)
                total_outputs += 1

        except Exception as e:
            logger.error(f"Failed: {wav}: {e}")

    logger.info(f"Done. {total_outputs} clips in {augmented_dir}")


if __name__ == "__main__":
    main()
