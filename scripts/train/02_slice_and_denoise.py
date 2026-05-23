#!/usr/bin/env python3
"""Slice audio into clips, remove silence, denoise.

Input:  data/training/raw/*.wav (or subdirectories)
Output: data/training/processed/*.wav

Uses:
- librosa for audio I/O and silence detection
- scipy.signal for basic noise gate
"""
import argparse
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import yaml
from loguru import logger


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def detect_silence_ranges(audio: np.ndarray, sr: int,
                           threshold: float, min_silence_len: float) -> list[tuple[int, int]]:
    """Detect silent regions in audio.
    
    Returns list of (start_sample, end_sample) for each silent region.
    """
    frame_length = int(sr * 0.05)  # 50ms frames
    hop_length = frame_length // 2
    rms = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
    threshold_linear = 10 ** (threshold / 20)  # Convert dB to linear
    is_silent = rms < threshold_linear
    
    # Find contiguous silent regions
    silent_regions = []
    min_frames = int(min_silence_len * sr / hop_length)
    start = None
    for i, silent in enumerate(is_silent):
        if silent and start is None:
            start = i
        elif not silent and start is not None:
            if i - start >= min_frames:
                silent_regions.append((start * hop_length, i * hop_length))
            start = None
    if start is not None and len(is_silent) - start >= min_frames:
        silent_regions.append((start * hop_length, len(is_silent) * hop_length))
    
    return silent_regions


def slice_audio(input_path: Path, output_dir: Path,
                config: dict) -> list[Path]:
    """Slice audio into non-silent segments."""
    audio_cfg = config["audio"]
    sr = audio_cfg["target_sr"]
    threshold = audio_cfg["silence_threshold"]
    min_dur = audio_cfg["min_duration"]
    max_dur = audio_cfg["max_duration"]
    
    logger.info(f"Processing: {input_path}")
    audio, orig_sr = librosa.load(str(input_path), sr=None, mono=True)
    
    # Resample if needed
    if orig_sr != sr:
        audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=sr)
    
    # Detect and remove silence
    silent_ranges = detect_silence_ranges(audio, sr, threshold, min_silence_len=0.5)
    if not silent_ranges:
        # No silence found — use whole file if within limits
        if len(audio) / sr >= min_dur:
            output_path = output_dir / f"{input_path.stem}.wav"
            sf.write(str(output_path), audio, sr)
            return [output_path]
        return []
    
    # Extract non-silent segments
    outputs = []
    prev_end = 0
    for seg_idx, (start, end) in enumerate(silent_ranges):
        segment = audio[prev_end:start]
        if len(segment) / sr >= min_dur:
            # If segment > max_dur, split further
            if len(segment) / sr > max_dur:
                midpoint = len(segment) // 2
                for part_idx, split_point in enumerate([0, midpoint]):
                    part = segment[split_point:split_point + midpoint]
                    if len(part) / sr >= min_dur:
                        output_path = output_dir / f"{input_path.stem}_seg{seg_idx}_p{part_idx}.wav"
                        sf.write(str(output_path), part, sr)
                        outputs.append(output_path)
            else:
                output_path = output_dir / f"{input_path.stem}_seg{seg_idx}.wav"
                sf.write(str(output_path), segment, sr)
                outputs.append(output_path)
        prev_end = end
    
    # Handle trailing audio after last silence
    trailing = audio[prev_end:]
    if len(trailing) / sr >= min_dur:
        output_path = output_dir / f"{input_path.stem}_trail.wav"
        sf.write(str(output_path), trailing, sr)
        outputs.append(output_path)
    
    logger.info(f"  -> {len(outputs)} segments from {input_path.name}")
    return outputs


def main():
    parser = argparse.ArgumentParser(description="Slice and denoise audio")
    parser.add_argument("--config", default=None, help="Override config path")
    args = parser.parse_args()
    
    config = load_config()
    raw_dir = Path(config["data"]["raw_dir"])
    processed_dir = Path(config["data"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    audio_files = list(raw_dir.rglob("*.wav")) + list(raw_dir.rglob("*.flac")) + list(raw_dir.rglob("*.mp3"))
    if not audio_files:
        logger.warning(f"No audio files found in {raw_dir}")
        return
    
    all_outputs = []
    for fpath in audio_files:
        try:
            outputs = slice_audio(fpath, processed_dir, config)
            all_outputs.extend(outputs)
        except Exception as e:
            logger.error(f"Failed to process {fpath}: {e}")
    
    total_dur = sum(float(librosa.get_duration(path=str(p))) for p in all_outputs) if all_outputs else 0
    logger.info(f"Done. {len(all_outputs)} clips in {processed_dir}")
    logger.info(f"Total duration: {total_dur:.1f}s")


if __name__ == "__main__":
    main()
