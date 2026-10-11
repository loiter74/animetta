"""Measure isolated cold/warm core installations without changing user caches."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

INVENTORY = """import importlib.metadata as m, json, sys
assert sys.version_info >= (3, 13)
print(json.dumps(sorted((d.metadata['Name'], d.version) for d in m.distributions())))
"""


def execute(command: list[str], environment: dict[str, str], log: Path) -> dict[str, Any]:
    """Run a bounded sample and preserve its public package-manager output."""
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=600
        )
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or b"") + (error.stderr or b"")
        log.write_bytes(output)
        return {"seconds": time.perf_counter() - started, "exit_code": 124, "error": "timeout"}
    log.write_text(result.stdout + result.stderr, encoding="utf-8", newline="\n")
    return {"seconds": time.perf_counter() - started, "exit_code": result.returncode}


def measure(args: argparse.Namespace) -> int:
    """Measure fresh environments, pairing each cold cache with a warm install."""
    assert sys.version_info >= (3, 13)
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    requirements = args.requirements.resolve()
    requirements_bytes = requirements.read_bytes()
    requirements = workspace / "requirements.txt"
    requirements.write_bytes(requirements_bytes)
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    uv_version = subprocess.check_output(["uv", "--version"], text=True).strip()
    if not uv_version.startswith("uv 0.11.19 "):
        raise RuntimeError("benchmark requires the project-pinned uv 0.11.19")
    environment = {key: value for key, value in os.environ.items() if not key.startswith("UV_")}
    environment.update(PYTHONUTF8="1", UV_LINK_MODE="copy")
    results: dict[str, Any] = {
        "phase": args.phase,
        "created_at": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "uv": uv_version,
        "index_url": args.index_url,
        "requirements": str(requirements),
        "requirements_sha256": hashlib.sha256(requirements_bytes).hexdigest(),
        "cache_definition": "one empty task cache per cold sample, reused by its warm pair",
        "samples": [],
        "complete": False,
    }

    def save() -> None:
        report.write_text(
            json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    save()
    for number in range(1, args.samples + 1):
        cache = workspace / f"cache-{number}"
        for mode in ("cold", "warm"):
            venv = workspace / f"{mode}-{number}"
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            sample: dict[str, Any] = {"mode": mode, "number": number}
            sample["create"] = execute(
                ["uv", "venv", "--python", sys.executable, str(venv)],
                environment,
                workspace / f"{mode}-{number}-create.log",
            )
            if sample["create"]["exit_code"]:
                results["samples"].append(sample)
                save()
                return 1
            sample["sync"] = execute(
                [
                    "uv",
                    "pip",
                    "sync",
                    "--python",
                    str(python),
                    "--cache-dir",
                    str(cache),
                    "--index-url",
                    args.index_url,
                    "--compile-bytecode",
                    str(requirements),
                ],
                environment,
                workspace / f"{mode}-{number}-sync.log",
            )
            results["samples"].append(sample)
            save()
            print(json.dumps({"phase": args.phase, **sample}), flush=True)
            if sample["sync"]["exit_code"]:
                return 1
            package_output = subprocess.check_output(
                [str(python), "-c", INVENTORY], env=environment, text=True, encoding="utf-8"
            )
            sample["packages"] = json.loads(package_output)
            sample["package_count"] = len(sample["packages"])
            sample["installed_bytes"] = sum(
                item.stat().st_size for item in venv.rglob("*") if item.is_file()
            )
            save()
    results["summary"] = {
        mode: {
            "samples": args.samples,
            "sync_seconds_median": statistics.median(
                item["sync"]["seconds"] for item in results["samples"] if item["mode"] == mode
            ),
            "sync_seconds_range": [
                min(item["sync"]["seconds"] for item in results["samples"] if item["mode"] == mode),
                max(item["sync"]["seconds"] for item in results["samples"] if item["mode"] == mode),
            ],
        }
        for mode in ("cold", "warm")
    }
    results["complete"] = True
    save()
    print(json.dumps(results["summary"]), flush=True)
    return 0


def main() -> int:
    """Parse explicit measurement inputs; refuse to overwrite an existing workspace."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--index-url", default="https://mirrors.aliyun.com/pypi/simple/")
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("samples must be positive")
    return measure(args)


if __name__ == "__main__":
    raise SystemExit(main())
