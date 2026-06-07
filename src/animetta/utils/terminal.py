"""
ANSI terminal color helpers.

Used by startup/stop scripts and any CLI tooling that needs colored output.
"""
import os
import platform
import sys


class Colors:
    """ANSI color codes for terminal output."""

    CYAN = "\033[0;36m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    RED = "\033[0;31m"
    MAGENTA = "\033[0;35m"
    GRAY = "\033[0;90m"
    NC = "\033[0m"  # No Color / reset

    @staticmethod
    def enabled() -> bool:
        """Check whether the current terminal supports ANSI colors."""
        if platform.system() != "Windows":
            return True
        if os.getenv("WT_SESSION") or os.getenv("TERM") or os.getenv("TERM_PROGRAM"):
            return True
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False


def info(msg: str) -> None:
    print(f"{Colors.CYAN}[INFO]{Colors.NC} {msg}" if Colors.enabled() else f"[INFO] {msg}")


def success(msg: str) -> None:
    print(f"{Colors.GREEN}[OK]{Colors.NC} {msg}" if Colors.enabled() else f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {msg}" if Colors.enabled() else f"[WARN] {msg}")


def error(msg: str) -> None:
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}" if Colors.enabled() else f"[ERROR] {msg}")
    sys.exit(1)
