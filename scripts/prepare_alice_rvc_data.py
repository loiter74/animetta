"""
Prepare Alice voice data for RVC training.

1. Reads all WAV files from the training set
2. Groups by source (filename prefix), sorts by sequence
3. Concatenates adjacent same-source segments into ~10s chunks
4. Resamples from 24000Hz → 44100Hz (safe input for RVC 40k training)
5. Saves to RVC dataset directory

Usage: PYTHONPATH=src python scripts/prepare_alice_rvc_data.py
"""
import glob
import os
import sys
import wave
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

try:
    import librosa
except ImportError:
    print("Installing librosa...")
    os.system(f"{sys.executable} -m pip install librosa -q")
    import librosa

# ── Config ──────────────────────────────────────────────
SOURCE_DIR = Path("E:/anima_data/tts_training/kuonji_arisu/training_ready/alice_training_set")
TARGET_DIR = Path("C:/Users/30262/RVC20240604Nvidia/dataset/alice")
TARGET_SR = 44100          # Safe input for RVC (will be resampled to 40k internally)
SOURCE_SR = 24000          # Current sample rate
TARGET_CHUNK_SEC = 10.0    # Target concatenation chunk size (seconds)
MIN_CHUNK_SEC = 3.0        # Minimum chunk to keep (discard shorter)


@dataclass
class AudioFile:
    path: Path
    filename: str
    prefix: str    # Source group (e.g., "01_FGO_语音集")
    seq: int       # Sequence number within group
    duration: float
    data: Optional[np.ndarray] = field(default=None, repr=False)


def extract_prefix(filename: str) -> str:
    """Extract source group from filename.
    
    Format: alice_XXXXX_FGO_Myroom_中文描述_XX.Xs.wav
    The source identifier is embedded in the Chinese description.
    We extract the stable prefix before the first Chinese-only segment.
    """
    # Try to extract source number like "01", "02" etc from patterns
    import re
    # Match patterns like "01_FGO_语音集" or just group by first few chars
    parts = filename.split("_")
    # alice_00001_FGO_Myroom_xxx → use "FGO_Myroom" as stable prefix
    # But segments from same source have sequential numbers
    # Simpler: group by everything up to the Chinese description
    m = re.match(r'(alice_\d+_)(.+?)(_\d+\.\d+s)?\.wav', filename)
    if m:
        return m.group(2)[:30]  # First 30 chars of the description part
    return filename[:40]


def group_by_source(files: list[Path]) -> list[AudioFile]:
    """Read file metadata and group by source."""
    audio_files = []
    
    for f in files:
        try:
            with wave.open(str(f)) as w:
                nframes = w.getnframes()
                sr = w.getframerate()
                duration = nframes / sr if sr > 0 else 0
                
            prefix = extract_prefix(f.name)
            # Extract sequence number from filename (e.g., alice_00001 → 1)
            seq = 0
            import re
            m = re.match(r'alice_(\d+)_', f.name)
            if m:
                seq = int(m.group(1))
            
            audio_files.append(AudioFile(
                path=f, filename=f.name, prefix=prefix, 
                seq=seq, duration=duration
            ))
        except Exception as e:
            print(f"  WARNING: Cannot read {f.name}: {e}")
    
    # Sort by prefix then sequence
    audio_files.sort(key=lambda x: (x.prefix, x.seq))
    return audio_files


def load_audio(af: AudioFile) -> np.ndarray:
    """Load and resample audio data."""
    audio, sr = librosa.load(str(af.path), sr=None, mono=True)
    if sr != TARGET_SR:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=TARGET_SR)
    return audio


def concatenate_groups(audio_files: list[AudioFile]) -> list[tuple[np.ndarray, float]]:
    """Concatenate same-source adjacent files into ~10s chunks.
    
    For groups with only 1 short segment (< TARGET_CHUNK_SEC), keep it as-is.
    For groups with multiple segments, concatenate adjacent ones into ~10s chunks.
    """
    chunks = []
    
    i = 0
    while i < len(audio_files):
        group_prefix = audio_files[i].prefix
        group = []
        
        # Collect consecutive files with same prefix
        while i < len(audio_files) and audio_files[i].prefix == group_prefix:
            group.append(audio_files[i])
            i += 1
        
        if not group:
            continue
        
        # If only one segment, keep as-is (don't discard short solo segments)
        if len(group) == 1:
            af = group[0]
            data = load_audio(af)
            dur = len(data) / TARGET_SR
            if dur >= 0.5:  # Keep anything > 0.5s
                data = np.pad(data, (0, int(TARGET_SR * 0.05)), mode='constant')  # tiny padding
                chunks.append((data, dur))
            continue
        
        # Multiple segments: concatenate into ~10s chunks
        current_chunk: list[np.ndarray] = []
        current_dur = 0.0
        
        for af in group:
            data = load_audio(af)
            dur = len(data) / TARGET_SR
            
            if current_dur + dur > TARGET_CHUNK_SEC and current_chunk:
                combined = np.concatenate(current_chunk)
                if current_dur >= 0.5:
                    chunks.append((combined, current_dur))
                current_chunk = []
                current_dur = 0.0
            
            current_chunk.append(data)
            current_dur += dur
        
        # Save remaining
        if current_chunk:
            combined = np.concatenate(current_chunk)
            if current_dur >= 0.5:
                chunks.append((combined, current_dur))
    
    return chunks


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """Peak normalize to -3dB to avoid clipping."""
    peak = np.abs(audio).max()
    if peak > 0:
        target_peak = 0.7  # -3dB
        audio = audio * (target_peak / peak)
    return audio


def save_wav(path: Path, audio: np.ndarray, sr: int):
    """Save as 16-bit PCM WAV."""
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio_int16.tobytes())


def main():
    print(f"Source: {SOURCE_DIR}")
    print(f"Target: {TARGET_DIR}")
    print(f"Target SR: {TARGET_SR} Hz, chunk: ~{TARGET_CHUNK_SEC}s\n")
    
    # Find files
    files = sorted(SOURCE_DIR.glob("*.wav"))
    print(f"Found {len(files)} WAV files")
    
    # Group and sort
    print("Grouping by source...")
    audio_files = group_by_source(files)
    
    # Count unique sources
    sources = set(af.prefix for af in audio_files)
    print(f"  {len(sources)} unique sources/groups")
    total_dur = sum(af.duration for af in audio_files)
    print(f"  Total duration: {total_dur/60:.1f} min")
    
    # Concatenate into chunks
    print(f"Concatenating into ~{TARGET_CHUNK_SEC}s chunks...")
    chunks = concatenate_groups(audio_files)
    chunk_durs = [d for _, d in chunks]
    print(f"  Produced {len(chunks)} chunks")
    print(f"  Total: {sum(chunk_durs)/60:.1f} min")
    print(f"  Avg: {np.mean(chunk_durs):.1f}s, Min: {min(chunk_durs):.1f}s, Max: {max(chunk_durs):.1f}s")
    
    # Save
    print(f"\nSaving to {TARGET_DIR}...")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    for idx, (audio, dur) in enumerate(chunks):
        audio = normalize_audio(audio)
        out_path = TARGET_DIR / f"alice_{idx+1:04d}.wav"
        save_wav(out_path, audio, TARGET_SR)
        
        if (idx + 1) % 100 == 0:
            print(f"  [{idx+1}/{len(chunks)}] saved")
    
    print(f"\nDone! {len(chunks)} files saved to {TARGET_DIR}")
    print(f"Total: {sum(chunk_durs)/60:.1f} min of {TARGET_SR}Hz mono audio")
    
    # Final stats
    total_bytes = sum(f.stat().st_size for f in TARGET_DIR.glob("*.wav"))
    print(f"Size: {total_bytes/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
