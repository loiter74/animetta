"""Export or verify pip requirements from the canonical uv lockfile."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = "# Generated from pyproject.toml and uv.lock; do not edit.\n# Update with: py -3.13 scripts/check_python_lock.py --write\n"
EXPORTS = {"requirements.txt": ["--no-dev"], "requirements-dev.txt": ["--group", "dev"]}


def export_requirements(root: Path, *, write: bool = False) -> None:
    """Check the lock and both exports, or explicitly regenerate the exports."""
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required; install the version declared in pyproject.toml")
    subprocess.run([uv, "lock", "--check", "--offline"], cwd=root, check=True)
    for filename, options in EXPORTS.items():
        result = subprocess.run(
            [
                uv,
                "export",
                "--locked",
                "--offline",
                "--format",
                "requirements.txt",
                "--no-emit-project",
                "--no-hashes",
                "--no-header",
                *options,
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        expected = HEADER + result.stdout
        path = root / filename
        if write:
            path.write_text(expected, encoding="utf-8", newline="\n")
        elif not path.exists() or path.read_text(encoding="utf-8") != expected:
            raise RuntimeError(f"{filename} differs from uv.lock; run with --write")


def main() -> int:
    """Run the canonical dependency export contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate both requirements files")
    args = parser.parse_args()
    try:
        export_requirements(ROOT, write=args.write)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"{exc}\n")
    print("Python dependency exports match uv.lock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
