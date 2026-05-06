#!/usr/bin/env python3
"""
ANSI color helpers for startup script output.
"""

import os
import platform
import sys


class Colors:
    """ANSI color codes"""
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    RED = '\033[0;31m'
    MAGENTA = '\033[0;35m'
    GRAY = '\033[0;90m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def enabled():
        """Check if colors are supported"""
        if platform.system() != "Windows":
            return True
        if os.getenv('WT_SESSION') or os.getenv('TERM') or os.getenv('TERM_PROGRAM'):
            return True
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except:
            return False


def info(msg):
    print(f"{Colors.CYAN}[INFO]{Colors.NC} {msg}" if Colors.enabled() else f"[INFO] {msg}")

def success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.NC} {msg}" if Colors.enabled() else f"[OK] {msg}")

def warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}" if Colors.enabled() else f"[WARN] {msg}")

def error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}" if Colors.enabled() else f"[ERROR] {msg}")
    sys.exit(1)
