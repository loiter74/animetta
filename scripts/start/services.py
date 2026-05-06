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
    python_exe = pm._get_venv_python(project_root)
    if python_exe != sys.executable:
        info(f"Using virtual environment: {python_exe}")
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


def start_web_config(project_root: Path, port: int = 8080) -> tuple:
    """Start the web configuration HTTP server."""
    info(f"Starting web configuration interface (port {port})...")
    python_exe = _get_venv_python(project_root)
    web_dir = project_root / "frontend" / "web"
    process = subprocess.Popen(
        [python_exe, "-m", "scripts.start.web_config_server", str(web_dir), str(port)],
        cwd=project_root, stdout=None, stderr=None,
    )
    return ("Web Config", process, port)


def start_vibe_voice(project_root: Path, pm: ProcessManager):
    """Start the VibeVoice TTS local inference server."""
    info("Starting VibeVoice TTS server (port 8765)...")
    python_exe = _get_venv_python(project_root)
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
