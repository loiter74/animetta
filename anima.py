#!/usr/bin/env python3
"""Anima CLI - character singing voice model toolkit.

Usage:
    python anima.py              # interactive menu
    python anima.py finetune     # fine-tune wizard
    python anima.py cover <url>  # AI cover
    python anima.py list         # show models
    python anima.py env          # check setup
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
RVC_PATHS = [
    Path(os.environ.get("RVC_PATH", "")),
    Path("C:/Users/30262/RVC20240604Nvidia"),
    Path.home() / "RVC20240604Nvidia",
]


class RVCEnv:
    def __init__(self):
        self.root = None
        self.python = None
        self.ok = False
        self._detect()

    def _detect(self):
        for p in RVC_PATHS:
            py = p / "runtime" / "python.exe"
            if py.exists():
                self.root = p
                self.python = str(py)
                break
        if self.root:
            try:
                r = subprocess.run(
                    [self.python, "-c", "import parselmouth"],
                    capture_output=True, text=True, timeout=10,
                    cwd=str(self.root),
                )
                self.ok = r.returncode == 0
            except Exception:
                self.ok = False

    @property
    def weights_dir(self):
        return (self.root / "weights") if self.root else Path(".")

    @property
    def logs_dir(self):
        return (self.root / "logs") if self.root else Path(".")

    def run(self, cmd, **kwargs):
        env = os.environ.copy()
        env["PATH"] = f"{self.root}\\runtime;{self.root};{env.get('PATH','')}"
        return subprocess.run(cmd, cwd=str(self.root), env=env, **kwargs)


# ── UI helpers ────────────────────────────────────────────────────

def title(text):    print(f"\n  {text}")
def ok(msg=""):     print(f"  [OK] {msg}")
def err(msg=""):    print(f"  [ERR] {msg}")
def info(msg):      print(f"    {msg}")
def ask(prompt, default=""):
    d = f" [{default}]" if default else ""
    return input(f"  {prompt}{d}: ").strip() or default
def confirm(text="Continue?"):
    return ask(f"{text} [y/N]")[:1].lower() == "y"


# ── Pipeline ──────────────────────────────────────────────────────

def run_pipeline(rvc, exp_name, data_dir, sr="48000", version="v2",
                 epochs=100, batch=16, pretrained_g=""):
    os.makedirs(str(rvc.logs_dir / exp_name), exist_ok=True)

    steps = [
        ("Preprocess audio", [
            "infer/modules/train/preprocess.py",
            data_dir, sr, "4", f"logs/{exp_name}", "False", "3.7",
        ]),
        ("Extract F0 (RMVPE)", [
            "infer/modules/train/extract/extract_f0_rmvpe.py",
            "4", "0", "1", f"logs/{exp_name}", version,
        ]),
        ("Extract features (ContentVec)", [
            "infer/modules/train/extract_feature_print.py",
            "0", "4", "assets/hubert/hubert_base.pt",
            "1", f"logs/{exp_name}", version, sr,
        ]),
    ]

    total = len(steps) + 1
    for i, (name, args) in enumerate(steps, 1):
        print(f"\n  [{i}/{total}] {name}...", end=" ", flush=True)
        r = rvc.run([rvc.python] + args, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print("ERR")
            info(r.stderr[-300:] if r.stderr else "")
            return False
        print("OK")

    print(f"\n  [{total}/{total}] Training ({epochs} epochs)...", end=" ", flush=True)
    cmd = [
        rvc.python, "infer/modules/train/train.py",
        "-e", exp_name, "-sr", sr, "-f0", "1",
        "-bs", str(batch), "-g", "0",
        "-te", str(epochs), "-se", "50",
        "-l", "1", "-c", "0", "-sw", "0", "-v", version,
    ]
    if pretrained_g:
        cmd += ["-pg", pretrained_g]

    t0 = time.time()
    r = rvc.run(cmd, capture_output=True, text=True, timeout=7200)
    elapsed = time.time() - t0
    if r.returncode != 0:
        print("ERR")
        info(r.stderr[-300:] if r.stderr else "")
        return False
    print(f"OK ({elapsed/60:.0f}min)")
    return True


def build_index(rvc, exp_name):
    import numpy as np
    try:
        import faiss
        from sklearn.cluster import MiniBatchKMeans
    except ImportError:
        info("faiss/sklearn not available, skip index")
        return False

    feat_dir = rvc.logs_dir / exp_name / "3_feature768"
    if not feat_dir.is_dir():
        info("No features, skip index")
        return False

    print(f"\n  [5/5] Build index...", end=" ", flush=True)
    try:
        npys = []
        for name in sorted(os.listdir(feat_dir)):
            npys.append(np.load(str(feat_dir / name)))
        if not npys:
            print("skip")
            return False
        big = np.concatenate(npys, 0)
        np.random.shuffle(big)
        n_ivf = min(int(big.shape[0] ** 0.5), 256)
        kmeans = MiniBatchKMeans(n_clusters=n_ivf, batch_size=10000, n_init="auto")
        kmeans.fit(big)
        index = faiss.IndexFlatL2(768)
        idx_ivf = faiss.IndexIVFFlat(index, 768, n_ivf)
        idx_ivf.train(big)
        idx_ivf.add(big)
        out = str(rvc.logs_dir / exp_name / f"{exp_name}.index")
        faiss.write_index(idx_ivf, out)
        print("OK")
        return True
    except Exception as e:
        print(f"ERR: {e}")
        return False


def deploy_model(rvc, exp_name):
    candidates = (
        list((rvc.logs_dir / exp_name).glob("*.pth")) +
        list((rvc.logs_dir / exp_name).glob("G_*.pth"))
    )
    if not candidates:
        return info("No checkpoint found")
    latest = max(candidates, key=lambda f: f.stat().st_mtime)
    dst = rvc.weights_dir / f"{exp_name}.pth"
    shutil.copy2(str(latest), str(dst))
    info(f"Model: {dst}")
    # Update singing.yaml
    cfg_path = PROJECT_ROOT / "config" / "singing.yaml"
    if cfg_path.exists():
        import yaml
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        cfg.setdefault("singing", {}).setdefault("rvc", {})["model_name"] = f"{exp_name}.pth"
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
        info(f"Config: {cfg_path}")


# ── Commands ──────────────────────────────────────────────────────

def cmd_list(rvc):
    title("Available Models")
    for m in sorted(rvc.weights_dir.glob("*.pth")):
        sz = m.stat().st_size / 1024 / 1024
        idx = rvc.logs_dir / f"{m.stem}.index"
        tag = " +index" if idx.exists() else ""
        print(f"  {m.stem:30s} {sz:6.1f} MB{tag}")


def cmd_finetune(rvc):
    models = sorted(rvc.weights_dir.glob("*.pth"))
    if not models:
        return info("No models yet.")
    print()
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m.stem}")
    choice = ask("Select model", "1")
    try:
        model = models[int(choice) - 1].stem
    except (ValueError, IndexError):
        model = models[0].stem

    name = ask("Experiment name", model)
    data = ask("Data directory", str(PROJECT_ROOT / "data/training/rvc_input"))
    epochs = ask("Epochs", "100")

    if not Path(data).is_dir():
        return err(f"Not found: {data}")
    wavs = list(Path(data).glob("*.wav"))
    if not wavs:
        return err("No WAV files found")

    total_size = sum(f.stat().st_size for f in wavs)
    info(f"Data: {len(wavs)} files, {total_size/1024/1024:.0f} MB")
    info(f"RVC:  {rvc.root}")
    info(f"Base model: {model}.pth")

    if not confirm("Start fine-tuning?"):
        return print("  Cancelled")

    ok_result = run_pipeline(rvc, name, data, epochs=int(epochs),
                             pretrained_g=f"weights/{model}.pth")
    if not ok_result:
        return err("Training failed")

    build_index(rvc, name)
    deploy_model(rvc, name)
    print(f"\n  Done! Model: weights/{name}.pth")


def cmd_cover(rvc, url=""):
    if not url:
        url = ask("Bilibili URL", "")
    if not url:
        return

    title("AI Cover")
    out_dir = PROJECT_ROOT / "data" / "singing" / "cover_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n  [1/4] Download...", end=" ", flush=True)
    r = subprocess.run([
        "yt-dlp", "--extract-audio", "--audio-format", "wav",
        "--audio-quality", "0", "-o", str(out_dir / "original.wav"), url,
    ], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return err("yt-dlp failed")
    print("OK")

    print("  [2/4] Separate vocals...", end=" ", flush=True)
    wrapper = str(PROJECT_ROOT / "scripts" / "demucs_fix.py")
    r = subprocess.run([
        sys.executable, wrapper,
        "-n", "htdemucs", "--two-stems", "vocals", "-d", "cpu",
        "-o", str(out_dir), str(out_dir / "original.wav"),
    ], capture_output=True, text=True, timeout=600,
       env={**os.environ, "TORCHAUDIO_BACKEND": "soundfile"})

    vocals = backing = None
    for root, _, files in os.walk(str(out_dir)):
        for f in files:
            if f == "vocals.wav":
                vocals = os.path.join(root, f)
            if f == "no_vocals.wav":
                backing = os.path.join(root, f)
    if not vocals:
        return err("Separation failed")
    print("OK")

    print("  [3/4] RVC convert...", end=" ", flush=True)
    model = ask("Model", "shige_utage")
    key = ask("Key shift (+/- semitones)", "0")
    conv = str(out_dir / "converted.wav")
    r = rvc.run([
        rvc.python, "tools/rvc_convert_wrapper.py",
        "--input_path", vocals,
        "--output_path", conv,
        "--model_name", f"{model}.pth",
        "--index_path", f"logs/{model}.index",
        "--f0_up_key", key,
        "--f0method", "rmvpe",
        "--index_rate", "0.75",
        "--filter_radius", "3",
        "--rms_mix_rate", "0.25",
        "--protect", "0.33",
    ], capture_output=True, text=True, timeout=1200)
    if r.returncode != 0 or not Path(conv).exists():
        return err("RVC failed")
    print("OK")

    print("  [4/4] Mix...", end=" ", flush=True)
    final = str(out_dir / "final.wav")
    r = subprocess.run([
        "ffmpeg", "-y", "-i", conv,
        "-i", backing or conv,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=3",
        "-ac", "2", final,
    ], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return err("Mix failed")
    print("OK")
    print(f"\n  Done: {final}")


def cmd_env(rvc):
    title("Environment")
    for name, ok_val in [
        ("RVC installation", rvc.root is not None),
        ("RVC dependencies", rvc.ok),
        ("ffmpeg", shutil.which("ffmpeg") is not None),
        ("yt-dlp", shutil.which("yt-dlp") is not None),
    ]:
        print(f"  {'[OK]' if ok_val else '[  ]'} {name}")
    if rvc.root:
        info(f"Path: {rvc.root}")
        info(f"Python: {rvc.python}")


MENU = """
  +----------------------------------+
  |   Anima - Voice Model Toolkit    |
  +----------------------------------+
  |  1. Train new model              |
  |  2. Fine-tune existing           |
  |  3. AI Cover (Bilibili URL)      |
  |  4. List models                  |
  |  5. Environment check            |
  |  0. Exit                         |
  +----------------------------------+
"""


def main():
    parser = argparse.ArgumentParser(description="Anima CLI")
    parser.add_argument("command", nargs="?", default="menu")
    parser.add_argument("url", nargs="?")
    args = parser.parse_args()

    rvc = RVCEnv()
    if not rvc.root:
        print("RVC not found. Set RVC_PATH or install to:")
        for p in RVC_PATHS[1:]:
            print(f"  {p}")
        return

    if args.command == "finetune":
        cmd_finetune(rvc)
    elif args.command == "cover":
        cmd_cover(rvc, args.url or "")
    elif args.command == "list":
        cmd_list(rvc)
    elif args.command == "env":
        cmd_env(rvc)
    else:
        print(MENU)
        c = ask("Select", "2")
        if c == "2": cmd_finetune(rvc)
        elif c == "3": cmd_cover(rvc)
        elif c == "4": cmd_list(rvc)
        elif c == "5": cmd_env(rvc)


if __name__ == "__main__":
    main()
