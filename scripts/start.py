#!/usr/bin/env python3
"""
Anima unified startup script.
Usage: python scripts/start.py [options]
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path so 'scripts.start' is importable
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from scripts.start import (
    Colors, info, success, warn, error,
    ProcessManager, open_browser,
    start_backend, start_vite, start_web_config, start_vibe_voice, start_gpt_sovits,
    get_tts_provider,
)


def main():
    parser = argparse.ArgumentParser(
        description="Anima unified startup script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/start.py                    # Start all services (backend + frontend + web config)
  python scripts/start.py --no-frontend      # Skip Vite frontend
  python scripts/start.py --backend-only     # Backend only
        """,
    )
    parser.add_argument('--mode', choices=['desktop', 'web'], default=None,
                        help=argparse.SUPPRESS)  # Deprecated, accepted for compatibility
    parser.add_argument('--backend-only', action='store_true', help='Start backend only')
    parser.add_argument('--no-backend', action='store_true', help='Skip backend')
    parser.add_argument('--no-web-config', action='store_true', help='Skip web config page')
    parser.add_argument('--no-frontend', action='store_true', help='Skip Vite frontend')
    parser.add_argument('--no-app', action='store_true', help=argparse.SUPPRESS)  # Deprecated
    parser.add_argument('--web-port', type=int, default=8080, help='Web config page port')
    parser.add_argument('--install', action='store_true', help='Reinstall dependencies')
    parser.add_argument('--dev', action='store_true', help='Enable DevTools')
    parser.add_argument('--no-tts-server', action='store_true', help='Skip TTS inference server')

    args = parser.parse_args()

    # Deprecation warnings
    if args.mode is not None:
        warn("--mode is deprecated and no longer has any effect. All services are started by default.")
    if args.no_app:
        warn("--no-app is deprecated, use --no-frontend instead")
        args.no_frontend = True

    # Project root
    os.chdir(_project_root)
    print()
    header = "Anima Startup Script"
    if Colors.enabled():
        print(f"{Colors.MAGENTA}{'=' * 50}{Colors.NC}")
        print(f"{Colors.MAGENTA}  {header}{Colors.NC}")
        print(f"{Colors.MAGENTA}{'=' * 50}{Colors.NC}")
    else:
        print('=' * 50)
        print(f'  {header}')
        print('=' * 50)
    print()

    # Check package manager
    pkg_manager = None
    use_shell = platform.system() == "Windows"
    for pm in ['pnpm', 'npm']:
        try:
            subprocess.run([pm, '--version'], capture_output=True, check=True, shell=use_shell)
            pkg_manager = pm
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    if pkg_manager:
        info(f"Package manager: {pkg_manager}")

    # Install dependencies if requested
    if args.install:
        info("Installing Python dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        if pkg_manager:
            info("Installing frontend dependencies...")
            subprocess.run([pkg_manager, 'install'], check=True, cwd='frontend', shell=use_shell)
        print()

    # Stop existing services
    pm = ProcessManager()
    info("Checking and stopping existing services...")
    pm.stop_processes_on_port(12394, "Backend")
    pm.stop_processes_on_port(9880, "GPT-SoVITS TTS")
    pm.stop_processes_on_port(8765, "VibeVoice TTS")
    pm.stop_processes_on_port(8080, "Web Config")
    pm.stop_processes_on_port(3000, "Frontend")
    print()

    started = []  # (name, process, port)

    try:
        # TTS server
        if not args.no_tts_server and not args.backend_only:
            provider = get_tts_provider(_project_root)
            if provider == "vibe_voice":
                info(f"TTS provider is {provider}, starting local inference server...")
                result = start_vibe_voice(_project_root, pm)
                if result:
                    started.append(result)
                    time.sleep(3)
            elif provider.startswith("gpt_sovits"):
                info(f"TTS provider is {provider}, starting GPT-SoVITS inference server...")
                result = start_gpt_sovits(_project_root, pm)
                if result:
                    started.append(result)
                    time.sleep(5)  # GPT-SoVITS takes longer to load
            else:
                info(f"TTS provider is {provider}, no local inference server needed")

        # Backend
        if not args.no_backend:
            started.append(start_backend(_project_root, pm))
            time.sleep(2)

        # Web config
        if not args.no_web_config and not args.backend_only:
            started.append(start_web_config(_project_root, args.web_port))
            time.sleep(1)

        # Frontend (always start unless explicitly skipped)
        if not args.no_frontend and not args.backend_only:
            if not pkg_manager:
                error("Frontend requires pnpm/npm")
            started.append(start_vite(_project_root))

        # Wait for services
        print()
        pm.wait_for_services()

        # Print status
        print()
        if Colors.enabled():
            print(f"{Colors.GREEN}{'=' * 50}{Colors.NC}")
            print(f"{Colors.GREEN}  All services started!{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 50}{Colors.NC}")
        else:
            print('=' * 50)
            print('  All services started!')
            print('=' * 50)
        print()

        urls = []
        if not args.no_backend:
            url = "http://localhost:12394"
            print(f"  Backend:     {Colors.CYAN}{url}{Colors.NC}" if Colors.enabled() else f"  Backend:     {url}")

        if not args.no_web_config and not args.backend_only:
            url = f"http://localhost:{args.web_port}"
            print(f"  Web Config:  {Colors.CYAN}{url}{Colors.NC}" if Colors.enabled() else f"  Web Config:  {url}")

        if not args.no_frontend and not args.backend_only:
            url = "http://localhost:3000"
            print(f"  Frontend:    {Colors.CYAN}{url}{Colors.NC}" if Colors.enabled() else f"  Frontend:    {url}")
            urls.append((url, 2))

        print()
        info("Press Ctrl+C to stop all services\n")

        # Auto-open browser
        open_browser(urls)

        # Wait loop
        while True:
            all_stopped = True
            for _, process, _ in started:
                if process.poll() is None:
                    all_stopped = False
                    try:
                        process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        pass
            if all_stopped:
                break

    except KeyboardInterrupt:
        pm.stop_all()


if __name__ == "__main__":
    main()
