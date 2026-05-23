#!/usr/bin/env python3
"""Data collection for character singing model training.

Supports three sources:
1. HuggingFace dataset — download Umamusume voice-text pairs
2. Bilibili covers — download audio + Demucs vocal separation
3. Game client — prints instructions for uma-voice-dataset-creator

Usage:
    # Download from HuggingFace (default)
    python scripts/train/01_collect_data.py --source huggingface

    # Download Bilibili songs (from URLs file)
    python scripts/train/01_collect_data.py --source bilibili --urls songs.txt

    # Game client instructions
    python scripts/train/01_collect_data.py --source game

    # All sources
    python scripts/train/01_collect_data.py --source all
"""
import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

import yaml
from loguru import logger


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


# ── HuggingFace ──────────────────────────────────────────────────


def collect_huggingface(raw_dir: Path) -> list[Path]:
    """Download Umamusume voice-text pairs from HuggingFace.
    
    Dataset: Plachta/Umamusume-voice-text-pairs
    Contains ~1000 Japanese voice-text pairs from the game.
    """
    logger.info("Collecting data from HuggingFace...")
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets not installed. Run: pip install datasets")
        return []

    out_dir = raw_dir / "huggingface"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        ds = load_dataset("Plachta/Umamusume-voice-text-pairs", split="train", trust_remote_code=True)
        logger.info(f"Loaded dataset: {len(ds)} samples")

        saved = 0
        for i, sample in enumerate(ds):
            # Filter for target character if name is specified
            char_name = _load_character_name()
            if char_name and char_name not in str(sample.get("speaker", "")).lower():
                continue

            audio = sample.get("audio")
            if audio is None:
                continue

            audio_bytes = audio.get("array")
            sr = audio.get("sampling_rate", 24000)
            if audio_bytes is None:
                continue

            import soundfile as sf
            import numpy as np
            path = out_dir / f"hf_{i:05d}.wav"
            sf.write(str(path), np.array(audio_bytes), sr)
            saved += 1

            # Save text metadata
            text = sample.get("text", "")
            if text:
                meta_path = path.with_suffix(".txt")
                meta_path.write_text(text, encoding="utf-8")

        logger.info(f"Saved {saved} files to {out_dir}")
        return list(out_dir.glob("*.wav"))

    except Exception as e:
        logger.error(f"HuggingFace download failed: {e}")
        return []


def _load_character_name() -> str | None:
    """Load character name from config for filtering."""
    try:
        config = load_config()
        return config.get("character", {}).get("display_name", "").lower() or None
    except Exception:
        return None


# ── Bilibili ─────────────────────────────────────────────────────


async def collect_bilibili(urls_file: str | None, urls: list[str] | None,
                           raw_dir: Path) -> list[Path]:
    """Download Bilibili audio and separate vocals.

    Uses yt-dlp for download and Demucs for source separation.
    If no URLs provided, prints instructions.
    """
    out_dir = raw_dir / "bilibili"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resolve URLs
    if urls_file:
        with open(urls_file) as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    elif not urls:
        logger.info("No URLs provided. Create a text file with Bilibili URLs (one per line) and pass --urls")
        print("""
Example songs.txt:
    https://www.bilibili.com/video/BV1xx411c7mD  # 诗歌剧角色歌
    https://www.bilibili.com/video/BV1yy411d8nE  # 游戏内歌曲
    https://www.bilibili.com/video/BV1zz411e9fA  # 翻唱
        """)
        return []

    # Download each URL
    results = []
    for url in urls:
        try:
            path = await _download_audio(url, out_dir)
            if path:
                results.append(path)
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")

    # Separate vocals
    vocal_files = []
    for audio_path in results:
        try:
            vocals = await _separate_vocals(audio_path)
            if vocals:
                vocal_files.append(vocals)
        except Exception as e:
            logger.warning(f"Vocal separation failed for {audio_path}: {e}")

    logger.info(f"Downloaded {len(results)} tracks, separated {len(vocal_files)} vocal tracks")
    return vocal_files


async def _download_audio(url: str, out_dir: Path) -> Path | None:
    """Download audio from Bilibili using yt-dlp."""
    logger.info(f"Downloading: {url}")
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", str(out_dir / "%(title)s.%(ext)s"),
        url,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"yt-dlp failed: {err}")

    # Find the downloaded file
    wavs = list(out_dir.glob("*.wav"))
    if not wavs:
        # Try subdirectory
        wavs = list(out_dir.rglob("*.wav"))
    return wavs[-1] if wavs else None


async def _separate_vocals(audio_path: Path) -> Path | None:
    """Separate vocals using Demucs."""
    logger.info(f"Separating vocals: {audio_path.name}")
    output_dir = audio_path.parent / "separated"
    output_dir.mkdir(exist_ok=True)

    cmd = [
        sys.executable, "-m", "demucs",
        "-n", "htdemucs",
        "--two-stems", "vocals",
        "-d", "cpu",
        "-o", str(output_dir),
        str(audio_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**__import__("os").environ, "TORCHAUDIO_BACKEND": "soundfile"},
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning(f"Demucs failed: {stderr.decode('utf-8','replace')[:300]}")
        return None

    # Find output
    stem = audio_path.stem
    demucs_out = output_dir / "htdemucs" / stem / "vocals.wav"
    if demucs_out.exists():
        dest = audio_path.parent / f"{stem}_vocals.wav"
        import shutil
        shutil.copy2(str(demucs_out), str(dest))
        logger.info(f"Vocals saved: {dest}")
        return dest
    return None


# ── Game Client ──────────────────────────────────────────────────


def print_game_instructions():
    """Print instructions for extracting game voice data."""
    instructions = """
╔══════════════════════════════════════════════════════════════╗
║          赛马娘游戏语音提取指南                               ║
╚══════════════════════════════════════════════════════════════╝

前提条件:
  1. 安装了 Windows 版赛马娘游戏 (DMM Games)
  2. 游戏安装目录下有 .acb 音频包文件

工具: uma-voice-dataset-creator
  https://github.com/sumomomomomo/uma-voice-dataset-creator

步骤:
  1. 克隆仓库:
     git clone https://github.com/sumomomomomo/uma-voice-dataset-creator

  2. 安装依赖:
     pip install -r requirements.txt

  3. 提取语音:
     python main.py --character "诗歌剧" --output "./extracted_voices"

  4. 将提取的 .wav 文件复制到:
     data/training/raw/game/

注意事项:
  - 提取出来的语音通常是短句 (2-10秒), 非常适合训练
  - 会包含各种情绪和语气, 覆盖丰富的音色变化
  - 如果提示缺少 Unity 库, 需要安装 Unity 并运行一次游戏来解包

替代: HuggingFace 已有提取好的数据集
  如果不想自己提取, 可以直接:
  python scripts/train/01_collect_data.py --source huggingface
"""
    print(instructions)


# ── Main ─────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Collect training data for character singing model")
    parser.add_argument("--source", choices=["huggingface", "bilibili", "game", "all"],
                        default="all", help="Data source to collect from")
    parser.add_argument("--urls", type=str, default=None,
                        help="File with Bilibili URLs (one per line)")
    args = parser.parse_args()

    config = load_config()
    raw_dir = Path(config["data"]["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    total = 0

    if args.source in ("huggingface", "all"):
        files = collect_huggingface(raw_dir)
        total += len(files)

    if args.source in ("bilibili", "all"):
        files = asyncio.run(collect_bilibili(args.urls, None, raw_dir))
        total += len(files)

    if args.source in ("game", "all"):
        print_game_instructions()

    logger.info(f"Collection complete. {total} audio files in {raw_dir}")


if __name__ == "__main__":
    main()
