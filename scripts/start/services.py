#!/usr/bin/env python3
"""
Service startup functions for Anima.
Each function returns a (name, process, port) tuple.
"""

import os
import subprocess
import sys
from pathlib import Path

from .colors import info, warn
from .process import ProcessManager


def start_backend(project_root: Path, pm: ProcessManager) -> tuple:
    """Start the Socket.IO backend server on port 12394."""
    info("Starting backend Socket.IO server (port 12394)...")
    python_exe = sys.executable
    src_path = project_root / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_path)
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(
        [python_exe, "-m", "anima.core.socketio_server"],
        cwd=project_root, env=env, stdout=None, stderr=None,
    )
    return ("Backend", process, 12394)


def start_vite(project_root: Path) -> tuple:
    """Start the Vite frontend dev server."""
    info("Starting Vite frontend (Vue 3 + Vite)...")
    frontend_dir = project_root / "frontend"
    node_modules = frontend_dir / "node_modules"
    needs_install = False
    if not node_modules.exists():
        warn("Frontend dependencies not installed, installing...")
        needs_install = True
    else:
        key_dept = frontend_dir / "node_modules" / "@vitejs" / "plugin-vue"
        if not key_dept.exists():
            info("Dependencies changed, updating...")
            needs_install = True
    if needs_install:
        subprocess.run(["pnpm", "install"], cwd=frontend_dir, shell=True, check=True)
    process = subprocess.Popen(
        ["pnpm", "run", "dev"], cwd=frontend_dir, shell=True, stdout=None, stderr=None,
    )
    return ("Frontend", process, None)


def start_vibe_voice(project_root: Path, pm: ProcessManager):
    """Start the VibeVoice TTS local inference server."""
    info("Starting VibeVoice TTS server (port 8765)...")
    python_exe = sys.executable
    server_script = project_root / "scripts" / "vibe_voice_server.py"
    model_path = "E:/anima_data/models/VibeVoice/VibeVoice-1.5B"
    if not server_script.exists():
        warn(f"VibeVoice server script not found: {server_script}")
        return None
    if not os.path.isdir(model_path):
        warn(f"VibeVoice model directory not found: {model_path}")
        return None
    process = subprocess.Popen(
        [python_exe, str(server_script), "--port", "8765",
         "--model", model_path, "--device", "cuda"],
        cwd=project_root, stdout=None, stderr=None,
    )
    return ("VibeVoice TTS", process, 8765)


def get_tts_provider(project_root: Path) -> str:
    """Read the TTS provider from config.yaml."""
    try:
        import yaml
        cfg_path = project_root / "config" / "config.yaml"
        with open(cfg_path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        return (cfg or {}).get('services', {}).get('tts', 'edge')
    except Exception:
        return 'edge'


def get_gpt_sovits_config(project_root: Path) -> dict:
    """Read GPT-SoVITS server config from config.yaml."""
    try:
        import yaml
        cfg_path = project_root / "config" / "config.yaml"
        with open(cfg_path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        gs_cfg = (cfg or {}).get('system', {}).get('gpt_sovits', {})
        return {
            'path': gs_cfg.get('path', ''),
            'python': gs_cfg.get('python', ''),
            'port': gs_cfg.get('port', 9880),
        }
    except Exception:
        return {'path': '', 'python': '', 'port': 9880}


def _detect_gpt_sovits_path(project_root: Path, configured_path: str) -> str:
    """Auto-detect GPT-SoVITS repo path."""
    if configured_path:
        return configured_path
    # Common locations
    candidates = [
        project_root.parent / "GPT-SoVITS",
        project_root.parent / "GPT_SoVITS",
        project_root.parent / "gpt-sovits",
        Path(os.path.expanduser("~")) / "GPT-SoVITS",
        Path(os.path.expanduser("~")) / "gpt-sovits",
        Path("E:/GPT-SoVITS"),
    ]
    for p in candidates:
        if (p / "api_v2.py").exists():
            return str(p)
    return ""


def _find_gpt_sovits_python(repo_path: str) -> str:
    """Find the Python interpreter for GPT-SoVITS conda env."""
    # Try conda environment first
    conda_envs = [
        Path.home() / "miniconda3" / "envs" / "gpt-sovits" / "bin" / "python",
        Path.home() / "miniconda3" / "envs" / "gpt-sovits" / "python.exe",
        Path.home() / "anaconda3" / "envs" / "gpt-sovits" / "bin" / "python",
        Path.home() / "anaconda3" / "envs" / "gpt-sovits" / "python.exe",
    ]
    for p in conda_envs:
        if p.exists():
            return str(p)
    # Fall back to conda run
    return ""


def start_gpt_sovits(project_root: Path, pm: ProcessManager):
    """Start the GPT-SoVITS api_v2.py inference server."""
    gs_cfg = get_gpt_sovits_config(project_root)
    repo_path = _detect_gpt_sovits_path(project_root, gs_cfg['path'])
    port = gs_cfg['port']

    if not repo_path:
        warn(
            "GPT-SoVITS repo not found. Set system.gpt_sovits.path in config.yaml "
            "or clone GPT-SoVITS alongside the Anima project."
        )
        return None

    info(f"Starting GPT-SoVITS api_v2.py (port {port})...")

    python_exe = gs_cfg['python'] or _find_gpt_sovits_python(repo_path)
    tts_infer_cfg = os.path.join(repo_path, "GPT_SoVITS", "configs", "tts_infer.yaml")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if python_exe:
        # Direct Python executable (conda env or venv)
        process = subprocess.Popen(
            [python_exe, "api_v2.py", "-a", "127.0.0.1", "-p", str(port),
             "-c", tts_infer_cfg],
            cwd=repo_path, env=env, stdout=None, stderr=None,
        )
    else:
        # Fallback: try conda run
        try:
            process = subprocess.Popen(
                ["conda", "run", "-n", "gpt-sovits", "python", "api_v2.py",
                 "-a", "127.0.0.1", "-p", str(port), "-c", tts_infer_cfg],
                cwd=repo_path, env=env, stdout=None, stderr=None,
            )
        except FileNotFoundError:
            warn(
                "conda not found and no GPT-SoVITS Python interpreter configured. "
                "Set system.gpt_sovits.python in config.yaml."
            )
            return None

    return ("GPT-SoVITS", process, port)


def _get_venv_python(project_root: Path) -> str:
    """Resolve the venv Python path or fall back to system Python."""
    venv_paths = [
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "bin" / "python",
        project_root / "venv" / "Scripts" / "python.exe",
        project_root / "venv" / "bin" / "python",
    ]
    for p in venv_paths:
        if p.exists():
            return str(p)
    return sys.executable
