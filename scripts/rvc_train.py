"""
RVC Training Pipeline — Reusable Voice Model Trainer

Generalized from rvc_train_alice.py. Trains a new RVC voice model from
prepared WAV audio files.

Usage:
    python scripts/rvc_train.py voice_name \\
        --source-dir dataset/my_voice \\
        --sr 40k --epochs 200 --batch-size 8

After training:
    - Model: C:/Users/30262/RVC20240604Nvidia/weights/{voice_name}.pth
    - Index: C:/Users/30262/RVC20240604Nvidia/logs/{voice_name}/added_*.index

Then update config/services.yaml vc.rvc to use the new model:
    model_path: "C:/Users/30262/RVC20240604Nvidia/weights/{voice_name}.pth"
    index_path: "C:/Users/30262/RVC20240604Nvidia/logs/{voice_name}/added_*.index"
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


# ── Defaults ──────────────────────────────────────────────
RVC_ROOT = Path(r"C:\Users\30262\RVC20240604Nvidia")
PYTHON_EXE = RVC_ROOT / "runtime" / "python.exe"

DEFAULT_SR = "40k"
DEFAULT_SR_NUM = 40000
DEFAULT_VERSION = "v2"
DEFAULT_N_PROC = 8
DEFAULT_BATCH_SIZE = 8
DEFAULT_EPOCHS = 200
DEFAULT_SAVE_EPOCH = 10


def run(cmd: str, desc: str, cwd: Path, timeout: int = 3600) -> None:
    """Run a command with progress display."""
    print(f"\n{'=' * 60}")
    print(f"  {desc}")
    print(f"  CMD: {cmd[:120]}...")
    print(f"{'=' * 60}")
    t0 = time.time()
    result = subprocess.run(cmd, shell=True, cwd=str(cwd),
                            capture_output=False, timeout=timeout)
    elapsed = time.time() - t0
    if result.returncode == 0:
        print(f"  ✅ DONE ({elapsed:.0f}s)")
    else:
        print(f"  ❌ FAILED ({elapsed:.0f}s, exit={result.returncode})")
        sys.exit(1)


def check_dataset(dataset_dir: Path) -> bool:
    """Verify dataset has WAV files."""
    wavs = list(dataset_dir.glob("*.wav"))
    if not wavs:
        print(f"  ❌ No WAV files found in {dataset_dir}")
        return False
    total = sum(f.stat().st_size for f in wavs) / 1024 / 1024
    print(f"  {len(wavs)} WAV files ({total:.1f} MB)")
    return True


# ── Stage 1: Preprocess ───────────────────────────────────
def stage_preprocess(exp_dir: str, dataset_dir: str, sr_num: int, n_proc: int):
    run(
        f'"{PYTHON_EXE}" infer/modules/train/preprocess.py '
        f'"{dataset_dir}" {sr_num} {n_proc} "{exp_dir}" False 3.7',
        "Stage 1: Preprocess (slice + normalize)", cwd=RVC_ROOT
    )


# ── Stage 2: F0 Extraction ────────────────────────────────
def stage_extract_f0(exp_dir: str):
    run(
        f'"{PYTHON_EXE}" infer/modules/train/extract/extract_f0_rmvpe.py '
        f'1 0 0 "{exp_dir}" True',
        "Stage 2: F0 extraction (RMVPE GPU)", cwd=RVC_ROOT,
        timeout=7200
    )


# ── Stage 3: HuBERT Features ──────────────────────────────
def stage_extract_feature(exp_dir: str, version: str):
    run(
        f'"{PYTHON_EXE}" infer/modules/train/extract_feature_print.py '
        f'cuda 1 0 0 "{exp_dir}" {version} True',
        "Stage 3: HuBERT feature extraction", cwd=RVC_ROOT,
        timeout=7200
    )


# ── Stage 3.5: Filelist + Config ──────────────────────────
def stage_filelist(exp_dir: str, version: str, sr: str):
    gt_dir = Path(exp_dir) / "0_gt_wavs"
    f0_dir = Path(exp_dir) / "2a_f0"
    f0nsf_dir = Path(exp_dir) / "2b-f0nsf"
    feat_dir = Path(exp_dir) / ("3_feature768" if version == "v2" else "3_feature256")

    names = set(f.stem for f in gt_dir.glob("*.wav"))
    names &= set(f.stem for f in feat_dir.glob("*.npy"))
    names &= set(f.stem for f in f0_dir.glob("*"))
    names &= set(f.stem for f in f0nsf_dir.glob("*"))

    filelist_path = Path(exp_dir) / "filelist.txt"
    with open(filelist_path, "w") as f:
        for name in sorted(names):
            f.write(f"{gt_dir.as_posix()}/{name}.wav|")
            f.write(f"{feat_dir.as_posix()}/{name}.npy|")
            f.write(f"{f0_dir.as_posix()}/{name}.wav.npy|")
            f.write(f"{f0nsf_dir.as_posix()}/{name}.wav.npy|")
            f.write("0\n")
    print(f"  filelist.txt: {len(names)} entries")

    config_src = Path(f"configs/{version}/{sr}.json")
    config_dst = Path(exp_dir) / "config.json"
    shutil.copy(config_src, config_dst)
    print(f"  config.json copied from {config_src}")


# ── Stage 4: Train ────────────────────────────────────────
def stage_train(exp_name: str, sr: str, batch_size: int,
                epochs: int, save_epoch: int, version: str):
    train_cmd = (
        f'"{PYTHON_EXE}" infer/modules/train/train.py '
        f'-e "{exp_name}" -sr "{sr}" -f0 1 -bs {batch_size} '
        f'-g "0" -te {epochs} -se {save_epoch} '
        f'-pg "assets/pretrained_v2/f0G{sr}.pth" '
        f'-pd "assets/pretrained_v2/f0D{sr}.pth" '
        f'-l 0 -c 1 -sw 1 -v "{version}"'
    )
    timeout = max(epochs * 30, 3600)  # ~30s/epoch, min 1h
    run(train_cmd, f"Stage 4: Train ({epochs} epochs, bs={batch_size})",
        cwd=RVC_ROOT, timeout=timeout)


# ── Stage 5: Build FAISS Index ────────────────────────────
def stage_build_index(exp_name: str, exp_dir: str, version: str) -> Optional[str]:
    try:
        import numpy as np
        import faiss
    except ImportError as e:
        print(f"  ⚠️  faiss not available, skipping index: {e}")
        return None

    feat_subdir = "3_feature768" if version == "v2" else "3_feature256"
    feature_dir = Path(exp_dir) / feat_subdir
    npys = sorted(feature_dir.glob("*.npy"))
    print(f"  Loading {len(npys)} feature files...")

    big_npy = np.concatenate([np.load(f) for f in npys], axis=0)
    np.random.shuffle(big_npy)
    vec_dim = big_npy.shape[1]
    print(f"  Vectors: {big_npy.shape[0]}, dim: {vec_dim}")

    n_ivf = min(int(16 * np.sqrt(big_npy.shape[0])), big_npy.shape[0] // 39)
    print(f"  n_ivf: {n_ivf}")

    index = faiss.index_factory(vec_dim, f"IVF{n_ivf},Flat")
    index_ivf = faiss.extract_index_ivf(index)
    index_ivf.nprobe = 1
    index.train(big_npy)

    batch_size_faiss = 8192
    for i in range(0, big_npy.shape[0], batch_size_faiss):
        index.add(big_npy[i:i + batch_size_faiss])

    index_path = f"logs/{exp_name}/added_IVF{n_ivf}_Flat_nprobe_1_{exp_name}_{version}.index"
    faiss.write_index(index, str(RVC_ROOT / index_path))
    print(f"  Index saved: {index_path}")
    return index_path


# ── Data Preparation ──────────────────────────────────────
def prepare_data(source_dir: str, dataset_dir: str, target_sr: int = 44100) -> None:
    """Copy and normalize WAV files from source to RVC dataset directory."""
    import numpy as np

    try:
        import librosa
    except ImportError:
        os.system(f"{sys.executable} -m pip install librosa -q")
        import librosa

    src = Path(source_dir)
    dst = Path(dataset_dir)
    dst.mkdir(parents=True, exist_ok=True)

    wavs = sorted(src.glob("*.wav")) + sorted(src.glob("*.mp3")) + sorted(src.glob("*.flac"))
    if not wavs:
        print(f"  ❌ No audio files found in {src}")
        sys.exit(1)

    print(f"  Preparing {len(wavs)} files → {dst}")
    for i, f in enumerate(wavs):
        audio, sr = librosa.load(str(f), sr=None, mono=True)
        if sr != target_sr:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        # Normalize to -3dB
        peak = np.abs(audio).max()
        if peak > 0:
            audio = audio * (0.7 / peak)
        audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

        out_path = dst / f"{f.stem}_{i+1:04d}.wav"
        import wave
        with wave.open(str(out_path), 'w') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(target_sr)
            w.writeframes(audio_int16.tobytes())

        if (i + 1) % 50 == 0:
            print(f"    [{i+1}/{len(wavs)}]")

    print(f"  ✅ {len(wavs)} files prepared in {dst}")


# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Train a new RVC voice model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick train from prepared dataset
  python scripts/rvc_train.py myvoice --dataset myvoice_data

  # Train with data preparation (from raw audio sources)
  python scripts/rvc_train.py myvoice --source-dir raw_audio/bob --prepare

  # Fast train for testing
  python scripts/rvc_train.py myvoice --dataset myvoice_data --epochs 50 --batch-size 16

After training, update config:
  config/services.yaml → vc.rvc.model_path: "weights/myvoice.pth"
  config/singing.yaml → rvc.model_name: "myvoice.pth"
        """
    )
    parser.add_argument("name", help="Voice model name (used for weights/ path)")
    parser.add_argument("--dataset", default=None,
                        help="Path to prepared WAV files (inside RVC dataset/)")
    parser.add_argument("--source-dir", default=None,
                        help="Path to raw audio files to prepare")
    parser.add_argument("--prepare", action="store_true",
                        help="Run data preparation before training")
    parser.add_argument("--skip-prepare", action="store_true",
                        help="Skip data preparation (dataset already ready)")
    parser.add_argument("--sr", default=DEFAULT_SR, choices=["32k", "40k", "48k"],
                        help="Sample rate (default: 40k)")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                        help=f"Training epochs (default: {DEFAULT_EPOCHS})")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Batch size (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--save-every", type=int, default=DEFAULT_SAVE_EPOCH,
                        help=f"Save checkpoint every N epochs (default: {DEFAULT_SAVE_EPOCH})")
    parser.add_argument("--version", default=DEFAULT_VERSION,
                        choices=["v1", "v2"], help="RVC version (default: v2)")
    parser.add_argument("--n-proc", type=int, default=DEFAULT_N_PROC,
                        help=f"Preprocessing workers (default: {DEFAULT_N_PROC})")
    parser.add_argument("--rvc-root", default=str(RVC_ROOT),
                        help="RVC project root directory")
    parser.add_argument("--stages", default="1-5",
                        help="Stages to run: 1-5 (all), 2-5 (skip preprocess), 4 (train only), etc.")

    args = parser.parse_args()

    rvc_root = Path(args.rvc_root)
    python_exe = rvc_root / "runtime" / "python.exe"

    if not python_exe.exists():
        print(f"❌ Python not found at {python_exe}")
        print("   Make sure RVC is installed at the correct path")
        sys.exit(1)

    sr_map = {"32k": 32000, "40k": 40000, "48k": 48000}
    sr_num = sr_map[args.sr]
    exp_name = args.name
    exp_dir = f"logs/{exp_name}"
    dataset_name = args.dataset or args.name
    dataset_dir = str(rvc_root / "dataset" / dataset_name)

    print(r"""
    ╔══════════════════════════════════════════════════════╗
    ║           RVC Voice Model Training Pipeline          ║
    ╚══════════════════════════════════════════════════════╝
    """)
    print(f"  Voice:      {exp_name}")
    print(f"  Dataset:    {dataset_dir}")
    print(f"  Sample Rate:{args.sr} ({sr_num}Hz)")
    print(f"  Version:    {args.version}")
    print(f"  Epochs:     {args.epochs}")
    print(f"  Batch Size: {args.batch_size}")
    print(f"  Stages:     {args.stages}")
    print(f"  RVC Root:   {rvc_root}")

    # Check prerequisites
    os.chdir(str(rvc_root))

    # ── Data Preparation ────────────────────────────────
    if args.prepare and args.source_dir:
        print(f"\n{'█' * 60}")
        print("█ DATA PREPARATION")
        print(f"{'█' * 60}")
        prepare_data(args.source_dir, dataset_dir, sr_num)
    elif args.source_dir or args.prepare:
        print(f"\n{'█' * 60}")
        print("█ DATA PREPARATION (--prepare flag)")
        print(f"{'█' * 60}")
        if args.source_dir:
            prepare_data(args.source_dir, dataset_dir, sr_num)
        else:
            print("  Skipping — no --source-dir provided")

    # ── Training Stages ─────────────────────────────────
    stages = args.stages
    run_stages = set()
    for part in stages.split(","):
        if "-" in part:
            start, end = part.split("-")
            run_stages.update(range(int(start), int(end) + 1))
        else:
            run_stages.add(int(part))

    # Stage 1: Preprocess
    if 1 in run_stages:
        print(f"\n{'█' * 60}")
        print("█ STAGE 1: Preprocess (slice + normalize)")
        print(f"{'█' * 60}")
        if not check_dataset(Path(dataset_dir)):
            sys.exit(1)
        stage_preprocess(exp_dir, dataset_dir, sr_num, args.n_proc)

    # Stage 2: F0 Extraction
    if 2 in run_stages:
        stage_extract_f0(exp_dir)

    # Stage 3: HuBERT Features
    if 3 in run_stages:
        stage_extract_feature(exp_dir, args.version)

    # Stage 3.5: Filelist + Config
    if any(s in run_stages for s in [1, 2, 3]):
        print(f"\n{'█' * 60}")
        print("█ STAGE 3.5: Generate filelist.txt + config.json")
        print(f"{'█' * 60}")
        stage_filelist(exp_dir, args.version, args.sr)

    # Stage 4: Train
    if 4 in run_stages:
        stage_train(exp_name, args.sr, args.batch_size,
                    args.epochs, args.save_every, args.version)

    # Stage 5: Build Index
    if 5 in run_stages:
        print(f"\n{'█' * 60}")
        print("█ STAGE 5: Build FAISS Index")
        print(f"{'█' * 60}")
        index_path = stage_build_index(exp_name, exp_dir, args.version)

    # ── Summary ──────────────────────────────────────────
    print(f"\n{'█' * 60}")
    print("█ TRAINING PIPELINE COMPLETE")
    print(f"{'█' * 60}")
    print(f"\n  Model:  weights/{exp_name}.pth")
    print(f"  Index:  logs/{exp_name}/added_*.index")
    print(f"\n  Update config/services.yaml:")
    print(f"    vc.rvc.model_path = \"weights/{exp_name}.pth\"")
    print(f"    vc.rvc.index_path = \"logs/{exp_name}/added_*.index\"")
    print(f"\n  Update config/singing.yaml:")
    print(f"    rvc.model_name = \"{exp_name}.pth\"")
    print(f"    rvc.index_path = \"logs/{exp_name}/added_*.index\"")


if __name__ == "__main__":
    main()
