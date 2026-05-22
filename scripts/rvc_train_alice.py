"""
RVC Training Pipeline Automation — Alice Voice Model
Run from C:\Users\30262\RVC20240604Nvidia
Usage: python ../scripts/rvc_train_alice.py
"""
import subprocess
import sys
import os
import json
import shutil
import time
from pathlib import Path

PYTHON = r"C:\Users\30262\RVC20240604Nvidia\runtime\python.exe"
RVC_ROOT = Path(r"C:\Users\30262\RVC20240604Nvidia")
os.chdir(str(RVC_ROOT))

EXP_NAME = "alice"
EXP_DIR = f"logs/{EXP_NAME}"
SR = "40k"
SR_NUM = 40000
VERSION = "v2"
N_PROC = 8
BATCH_SIZE = 8  # RTX 5090 32GB
EPOCHS = 200
SAVE_EPOCH = 10

def run(cmd, desc, timeout=3600):
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"  CMD: {cmd[:120]}...")
    print(f"{'='*60}")
    t0 = time.time()
    result = subprocess.run(cmd, shell=True, cwd=str(RVC_ROOT), 
                           capture_output=False, timeout=timeout)
    elapsed = time.time() - t0
    if result.returncode == 0:
        print(f"  DONE in {elapsed:.0f}s (exit=0)")
    else:
        print(f"  FAILED in {elapsed:.0f}s (exit={result.returncode})")
        sys.exit(1)

# ── Stage 1: Preprocess ────────────────────────────
print("\n" + "█"*60)
print("█ STAGE 1: Preprocess (slice + normalize)")
print("█"*60)
run(
    f'"{PYTHON}" infer/modules/train/preprocess.py '
    f'"dataset/alice" {SR_NUM} {N_PROC} "{EXP_DIR}" False 3.7',
    "Preprocessing audio files"
)

# ── Stage 2: F0 Extraction (RMVPE GPU) ────────────
print("\n" + "█"*60)
print("█ STAGE 2: F0 Extraction (RMVPE GPU)")
print("█"*60)
run(
    f'"{PYTHON}" infer/modules/train/extract/extract_f0_rmvpe.py '
    f'1 0 0 "{EXP_DIR}" True',
    "Extracting F0 pitch with RMVPE"
)

# ── Stage 3: HuBERT Feature Extraction ─────────────
print("\n" + "█"*60)
print("█ STAGE 3: HuBERT Feature Extraction")
print("█"*60)
# Note: extract_feature_print uses different arg count based on GPU
# With explicit GPU, len(sys.argv) > 7
run(
    f'"{PYTHON}" infer/modules/train/extract_feature_print.py '
    f'cuda 1 0 0 "{EXP_DIR}" {VERSION} True',
    "Extracting HuBERT content features"
)

# ── Stage 3.5: Generate filelist + config ───────────
print("\n" + "█"*60)
print("█ STAGE 3.5: Generate filelist.txt + config.json")
print("█"*60)

gt_dir = Path(EXP_DIR) / "0_gt_wavs"
f0_dir = Path(EXP_DIR) / "2a_f0"
f0nsf_dir = Path(EXP_DIR) / "2b-f0nsf"
feat_dir = Path(EXP_DIR) / ("3_feature768" if VERSION == "v2" else "3_feature256")

# Match files across all directories
names = set(f.stem for f in gt_dir.glob("*.wav"))
names &= set(f.stem for f in feat_dir.glob("*.npy"))
names &= set(f.stem for f in f0_dir.glob("*"))
names &= set(f.stem for f in f0nsf_dir.glob("*"))

# Write filelist
spk_id = 0
filelist_path = Path(EXP_DIR) / "filelist.txt"
with open(filelist_path, "w") as f:
    for name in sorted(names):
        f.write(f"{gt_dir.as_posix()}/{name}.wav|")
        f.write(f"{feat_dir.as_posix()}/{name}.npy|")
        f.write(f"{f0_dir.as_posix()}/{name}.wav.npy|")
        f.write(f"{f0nsf_dir.as_posix()}/{name}.wav.npy|")
        f.write(f"{spk_id}\n")
print(f"  filelist.txt: {len(names)} entries")

# Copy config
config_src = Path(f"configs/{VERSION}/{SR}.json")
config_dst = Path(EXP_DIR) / "config.json"
shutil.copy(config_src, config_dst)
print(f"  config.json copied from {config_src}")

# ── Stage 4: Train Model ────────────────────────────
print("\n" + "█"*60)
print(f"█ STAGE 4: Train Model ({EPOCHS} epochs, bs={BATCH_SIZE})")
print(f"█ This will take 2-4 hours on RTX 5090")
print("█"*60)

train_cmd = (
    f'"{PYTHON}" infer/modules/train/train.py '
    f'-e "{EXP_NAME}" -sr "{SR}" -f0 1 -bs {BATCH_SIZE} '
    f'-g "0" -te {EPOCHS} -se {SAVE_EPOCH} '
    f'-pg "assets/pretrained_v2/f0G{SR}.pth" '
    f'-pd "assets/pretrained_v2/f0D{SR}.pth" '
    f'-l 0 -c 1 -sw 1 -v "{VERSION}"'
)
run(train_cmd, f"Training {EPOCHS} epochs", timeout=28800)  # 8h timeout

# ── Stage 5: Build Index ────────────────────────────
print("\n" + "█"*60)
print("█ STAGE 5: Build FAISS Index")
print("█"*60)

try:
    import numpy as np
    import faiss
    
    feature_dir = Path(EXP_DIR) / "3_feature768"
    npys = sorted(feature_dir.glob("*.npy"))
    print(f"  Loading {len(npys)} feature files...")
    
    big_npy = np.concatenate([np.load(f) for f in npys], axis=0)
    np.random.shuffle(big_npy)
    print(f"  Total vectors: {big_npy.shape[0]}, dim: {big_npy.shape[1]}")
    
    n_ivf = min(int(16 * np.sqrt(big_npy.shape[0])), big_npy.shape[0] // 39)
    print(f"  n_ivf: {n_ivf}")
    
    index = faiss.index_factory(768, f"IVF{n_ivf},Flat")
    index_ivf = faiss.extract_index_ivf(index)
    index_ivf.nprobe = 1
    index.train(big_npy)
    
    batch_size_faiss = 8192
    for i in range(0, big_npy.shape[0], batch_size_faiss):
        index.add(big_npy[i:i+batch_size_faiss])
    
    index_path = f"logs/{EXP_NAME}/added_IVF{n_ivf}_Flat_nprobe_1_{EXP_NAME}_v2.index"
    faiss.write_index(index, index_path)
    print(f"  Index saved: {index_path}")

except ImportError as e:
    print(f"  WARNING: {e} — skipping index (can run in RVC WebUI later)")

# ── Summary ──────────────────────────────────────────
print("\n" + "█"*60)
print("█ TRAINING PIPELINE COMPLETE")
print("█"*60)
print(f"\n  Model weights should be at: weights/{EXP_NAME}.pth")
print(f"  Index should be at: logs/{EXP_NAME}/added_*.index")
print(f"\n  Next: Update config/singing.yaml to use alice.pth")
