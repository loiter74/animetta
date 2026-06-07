"""
Voice Data Collector — Download & prepare training data for RVC voice models.

Supports:
  - YouTube / Bilibili video download (via yt-dlp)
  - Vocal separation (via Demucs)
  - Silence trimming and segmentation
  - Output: clean vocal WAV files ready for train/cli.py

Usage:
    # From a URL
    python scripts/collect_voice_data.py my_new_voice \\
        --url "https://www.bilibili.com/video/BVxxxx" \\
        --output dataset/my_new_voice

    # From existing audio files
    python scripts/collect_voice_data.py my_new_voice \\
        --source-dir raw_recordings/ \\
        --output dataset/my_new_voice

    # Skip separation (if audio is already clean vocals)
    python scripts/collect_voice_data.py my_new_voice \\
        --source-dir clean_vocals/ --no-separate
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


def run_cmd(cmd: list[str], desc: str, cwd: Optional[Path] = None, timeout: int = 3600):
    """Run a command and check exit code."""
    print(f"  {desc}...")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None, timeout=timeout)
    if result.returncode != 0:
        print(f"  ⚠️  {desc} failed: {result.stderr[:300]}")
        return False
    print(f"  ✅ {desc} done")
    return True


def check_yt_dlp() -> bool:
    """Check if yt-dlp is available."""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def download_audio(url: str, output_dir: Path) -> Optional[Path]:
    """Download best audio from a video URL."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio/best",
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", output_template,
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"  ❌ Download failed: {result.stderr[:300]}")
        return None

    # Find the downloaded file
    wavs = list(output_dir.glob("*.wav"))
    if wavs:
        return max(wavs, key=lambda f: f.stat().st_mtime)
    return None


def separate_vocals(input_path: Path, output_dir: Path) -> Optional[Path]:
    """Separate vocals using Demucs (if available) or MSST."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try demucs CLI first (common on Windows via pip install demucs)
    for demucs_cmd in ["demucs", "python -m demucs"]:
        try:
            cmd = demucs_cmd.split() + [
                "--two-stems", "vocals",
                "-o", str(output_dir),
                str(input_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                # demucs creates {output_dir}/{model_name}/{stem}/{file_stem}/
                for vocals_path in output_dir.rglob("vocals.wav"):
                    print(f"  ✅ Vocals extracted: {vocals_path}")
                    return vocals_path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    # Fallback: try MSST
    msst_root = Path(r"C:\Users\30262\Music-Source-Separation-Training")
    if msst_root.exists():
        print("  Using MSST for separation...")
        python_exe = sys.executable
        inference_script = msst_root / "inference.py"
        if inference_script.exists():
            cmd = [
                python_exe, str(inference_script),
                "--input_folder", str(input_path.parent),
                "--store_dir", str(output_dir),
                "--model_type", "mel_band_roformer",
                "--config_path", str(msst_root / "configs" / "config_vocals_mel_band_roformer.yaml"),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
            if result.returncode == 0:
                for vocals_path in output_dir.rglob("vocals.wav"):
                    return vocals_path

    print("  ⚠️  No separation engine available (install: pip install demucs)")
    return input_path  # Return original if separation fails


def trim_silence(input_dir: Path, output_dir: Path,
                 min_duration: float = 2.0, max_duration: float = 15.0,
                 silence_thresh: float = -40.0, min_silence: float = 0.5) -> int:
    """Trim silence and split long audio into segments."""
    try:
        import numpy as np
        try:
            import librosa
        except ImportError:
            os.system(f"{sys.executable} -m pip install librosa -q")
            import librosa
    except ImportError:
        print("  ❌ numpy/librosa required for audio processing")
        return 0

    import soundfile as sf

    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    audio_files = list(input_dir.glob("*.wav")) + list(input_dir.glob("*.flac"))
    for audio_path in audio_files:
        try:
            audio, sr = librosa.load(str(audio_path), sr=None, mono=True)
        except Exception:
            continue

        # Detect non-silent intervals
        intervals = librosa.effects.split(audio, top_db=-silence_thresh,
                                          frame_length=2048, hop_length=512)

        for start, end in intervals:
            segment = audio[start:end]
            dur = len(segment) / sr

            # Skip too short
            if dur < min_duration:
                continue

            # Split long segments
            if dur > max_duration:
                chunk_samples = int(max_duration * sr)
                for i in range(0, len(segment), chunk_samples):
                    chunk = segment[i:i + chunk_samples]
                    if len(chunk) / sr >= min_duration:
                        out_path = output_dir / f"{audio_path.stem}_{count:04d}.wav"
                        sf.write(str(out_path), chunk, sr)
                        count += 1
            else:
                out_path = output_dir / f"{audio_path.stem}_{count:04d}.wav"
                sf.write(str(out_path), segment, sr)
                count += 1

    print(f"  ✅ {count} segments extracted ({min_duration}s–{max_duration}s)")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Collect and prepare voice training data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From Bilibili video
  python scripts/collect_voice_data.py my_voice --url "https://www.bilibili.com/video/BVxxxx"

  # From local audio folder (skip download)
  python scripts/collect_voice_data.py my_voice --source-dir recordings/

  # From clean vocals (skip separation)
  python scripts/collect_voice_data.py my_voice --source-dir clean_vocals/ --no-separate

Output goes to: C:/Users/30262/RVC20240604Nvidia/dataset/{name}/
Ready for: python -m scripts.train.cli --character {name}
        """
    )
    parser.add_argument("name", help="Voice name (creates dataset/{name})")
    parser.add_argument("--url", help="Video URL to download audio from")
    parser.add_argument("--source-dir", help="Existing audio files directory")
    parser.add_argument("--output", default=None,
                        help="Output directory (default: RVC dataset/{name})")
    parser.add_argument("--no-separate", action="store_true",
                        help="Skip vocal separation (audio is already clean)")
    parser.add_argument("--no-trim", action="store_true",
                        help="Skip silence trimming")
    parser.add_argument("--min-duration", type=float, default=2.0,
                        help="Minimum segment duration in seconds")
    parser.add_argument("--max-duration", type=float, default=15.0,
                        help="Maximum segment duration in seconds")
    parser.add_argument("--keep-temp", action="store_true",
                        help="Keep intermediate files")

    args = parser.parse_args()

    rvc_root = Path(r"C:\Users\30262\RVC20240604Nvidia")
    final_output = Path(args.output) if args.output else (rvc_root / "dataset" / args.name)
    work_dir = Path(tempfile.mkdtemp(prefix=f"voice_{args.name}_")) if not args.keep_temp else Path(f"_work_{args.name}")
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"""
  ╔══════════════════════════════════════════╗
  ║     Voice Data Collector                ║
  ╚══════════════════════════════════════════╝
  Voice:   {args.name}
  Output:  {final_output}
  Source:  {args.url or args.source_dir or '(none)'}
  """)

    # Step 1: Get audio
    audio_files: list[Path] = []

    if args.url:
        print("\n── Step 1: Download ──")
        dl_dir = work_dir / "download"
        audio_path = download_audio(args.url, dl_dir)
        if audio_path:
            audio_files.append(audio_path)
        else:
            print("  ❌ Download failed")
            sys.exit(1)

    elif args.source_dir:
        print("\n── Step 1: Load source files ──")
        src = Path(args.source_dir)
        audio_files = list(src.glob("*.wav")) + list(src.glob("*.mp3")) + \
                      list(src.glob("*.flac")) + list(src.glob("*.m4a"))
        print(f"  Found {len(audio_files)} audio files")
    else:
        print("  ❌ Need --url or --source-dir")
        sys.exit(1)

    # Step 2: Separate vocals
    if not args.no_separate and audio_files:
        print("\n── Step 2: Separate vocals ──")
        sep_dir = work_dir / "separated"
        processed = []
        for f in audio_files:
            result = separate_vocals(f, sep_dir)
            if result:
                processed.append(result)
        if processed:
            audio_files = processed
        else:
            print("  ⚠️  Separation failed, using original audio")

    # Step 3: Trim silence & segment
    if not args.no_trim and audio_files:
        print("\n── Step 3: Trim silence ──")
        trim_dir = work_dir / "trimmed"
        # Work with directories if separation produced them
        for f in list(audio_files):
            if f.is_dir():
                count = trim_silence(f, trim_dir, args.min_duration, args.max_duration)
            else:
                count = trim_silence(Path(f.parent), trim_dir, args.min_duration, args.max_duration)
        if count > 0:
            audio_files = list(trim_dir.glob("*.wav"))

    # Step 4: Copy to final output
    print(f"\n── Step 4: Copy to {final_output} ──")
    final_output.mkdir(parents=True, exist_ok=True)
    copied = 0
    for f in audio_files:
        if f.suffix.lower() not in (".wav", ".flac"):
            continue
        dest = final_output / f.name
        if not dest.exists():
            import shutil
            shutil.copy2(f, dest)
            copied += 1
    print(f"  ✅ {copied} files copied")

    # Cleanup
    if not args.keep_temp:
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)

    # Summary
    total = sum(f.stat().st_size for f in final_output.glob("*.wav")) / 1024 / 1024
    duration = 0
    try:
        import wave
        for f in final_output.glob("*.wav"):
            with wave.open(str(f)) as w:
                duration += w.getnframes() / w.getframerate()
    except Exception:
        pass

    print(f"""
  ╔══════════════════════════════════════════╗
  ║  Data collection complete!              ║
  ╠══════════════════════════════════════════╣
  ║  Files:    {copied:>30d} ║
  ║  Size:     {total:>28.1f} MB ║
  ║  Duration: {duration/60:>28.1f} min ║
  ╠══════════════════════════════════════════╣
  ║  Next:                                  ║
  ║  python -m scripts.train.cli --character {args.name} ║
  ╚══════════════════════════════════════════╝
  """)


if __name__ == "__main__":
    main()
