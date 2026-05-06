#!/usr/bin/env python3
"""
Cross-platform process management for Anima startup.
"""

import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

from .colors import info, success, warn, error


class ProcessManager:
    """Cross-platform process management."""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.processes = []
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up signal handlers so Ctrl+C stops all child processes."""
        def handler(signum, frame):
            print("\n")
            self.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler)
        if self.is_windows and hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, handler)

    def find_processes_on_port(self, port):
        """Find PIDs occupying a given port."""
        pids = []

        if self.is_windows:
            try:
                ps_script = f"""
                Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue |
                    Where-Object {{ $_.State -eq "Listen" }} |
                    Select-Object -ExpandProperty OwningProcess
                """
                result = subprocess.run(
                    ['powershell', '-Command', ps_script],
                    capture_output=True, text=True, check=True
                )
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and line.isdigit():
                        pid = int(line)
                        if pid not in pids:
                            pids.append(pid)
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    result = subprocess.run(
                        ['netstat', '-ano'], capture_output=True, text=True, check=True
                    )
                    for line in result.stdout.split('\n'):
                        if f':{port}' in line and 'LISTENING' in line:
                            parts = line.split()
                            if len(parts) >= 5:
                                pid = int(parts[-1])
                                if pid not in pids:
                                    pids.append(pid)
                except subprocess.CalledProcessError:
                    pass
        else:
            try:
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True, text=True, check=True
                )
                pids = [int(pid.strip()) for pid in result.stdout.split('\n') if pid.strip()]
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        return pids

    def stop_process(self, pid, service_name):
        """Stop a process by PID."""
        if not pid:
            return True
        try:
            if self.is_windows:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True, capture_output=True)
            else:
                subprocess.run(['kill', '-9', str(pid)], check=True, capture_output=True)
            success(f"Stopped {service_name} (PID: {pid})")
            return True
        except subprocess.CalledProcessError as e:
            warn(f"Cannot stop process {pid}: {e}")
            return False

    def stop_processes_on_port(self, port, service_name):
        """Stop all processes occupying a port."""
        pids = self.find_processes_on_port(port)
        if not pids:
            return True
        info(f"Found {service_name} occupying port {port}: PID {pids}")
        for pid in pids:
            self.stop_process(pid, service_name)
            time.sleep(0.5)
        time.sleep(1)
        remaining = self.find_processes_on_port(port)
        if remaining:
            warn(f"Port {port} still occupied: {remaining}")
            return False
        return True

    def _get_venv_python(self, project_root):
        """Get venv Python or fall back to system Python."""
        venv_paths = [
            project_root / ".venv" / "Scripts" / "python.exe",
            project_root / ".venv" / "bin" / "python",
            project_root / "venv" / "Scripts" / "python.exe",
            project_root / "venv" / "bin" / "python",
        ]
        for venv_python in venv_paths:
            if venv_python.exists():
                return str(venv_python)
        return sys.executable

    def wait_for_services(self):
        """Wait for all started services to be ready."""
        if not self.processes:
            return
        info("Waiting for services to start...")
        time.sleep(2)
        for name, process, port in self.processes:
            if port:
                for _ in range(15):
                    if self.find_processes_on_port(port):
                        success(f"{name} ready (port {port})")
                        break
                    time.sleep(0.5)
                else:
                    warn(f"{name} may not have started correctly")

    def stop_all(self):
        """Stop all started services."""
        if not self.processes:
            return
        info("\nStopping all services...")
        for name, process, port in self.processes:
            try:
                if self.is_windows:
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                        capture_output=True, timeout=5
                    )
                else:
                    process.terminate()
                    process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        for name, process, port in self.processes:
            if port:
                self.stop_processes_on_port(port, name)
        self.processes.clear()
        success("All services stopped")
