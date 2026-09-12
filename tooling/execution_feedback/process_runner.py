from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path


def _write_receipt(path: Path, *, exit_code: int, started_at: str, elapsed_seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(
                {
                    "exit_code": exit_code,
                    "started_at": started_at,
                    "finished_at": datetime.now(UTC).isoformat(),
                    "elapsed_seconds": elapsed_seconds,
                },
                handle,
                sort_keys=True,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a leased command and persist its exit code.")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("a command is required after --")
    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    completed = subprocess.run(command, check=False)
    _write_receipt(
        args.receipt,
        exit_code=completed.returncode,
        started_at=started_at,
        elapsed_seconds=time.perf_counter() - started,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
