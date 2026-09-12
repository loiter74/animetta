"""Measure unchanged lifecycle implementations with the same external timing driver."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import html
import importlib.util
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def build_phases(contents: str) -> list[dict[str, object]]:
    """BuildKit steps overlap; their durations must never be summed as wall time."""
    steps: dict[str, dict[str, object]] = {}
    for line in contents.splitlines():
        match = re.match(r"^#(\d+) (.*)$", line)
        if not match:
            continue
        identifier, body = match.groups()
        if body.startswith("[") or body == "exporting to image":
            steps.setdefault(identifier, {"id": identifier, "description": body})
        elif body.startswith("DONE ") and identifier in steps:
            duration = re.fullmatch(r"DONE ([0-9.]+)s", body)
            if duration:
                steps[identifier]["seconds"] = float(duration[1])
                steps[identifier]["cached"] = False
        elif body == "CACHED" and identifier in steps:
            steps[identifier].update(seconds=0.0, cached=True)
    return list(steps.values())


def comparison(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    """Refuse a percentage when either side lacks successful comparable samples."""
    if before and after:
        for key in (
            "scenario",
            "driver_sha256",
            "browser_driver_sha256",
            "configuration_file_sha256",
            "profile",
            "platform",
            "python",
        ):
            if before.get(key) != after.get(key):
                raise ValueError(f"comparison conditions differ: {key}")
    old = before.get("median_seconds") if before else None
    new = after.get("median_seconds") if after else None
    result = {
        "before_seconds": old,
        "after_seconds": new,
        "seconds_saved": None,
        "reduction_percent": None,
        "speedup": None,
    }
    if old is not None and new is not None and old > 0 and new > 0:
        result.update(
            seconds_saved=old - new, reduction_percent=(old - new) / old * 100, speedup=old / new
        )
    return result


def compare(args: argparse.Namespace) -> int:
    before = json.loads(args.before.read_text(encoding="utf-8")) if args.before else None
    after = json.loads(args.after.read_text(encoding="utf-8")) if args.after else None
    result = comparison(before, after)
    result["scenario"] = (after or before or {}).get("scenario", "unmeasured")
    if args.predictions:
        predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
        forecast = predictions["scenarios"].get(result["scenario"], {})
        bounds = forecast.get("target_seconds")
        result["prediction_sha256"] = hashlib.sha256(args.predictions.read_bytes()).hexdigest()
        result["target_seconds"] = bounds
        actual = result["after_seconds"]
        result["prediction_error_seconds"] = (
            actual - statistics.mean(bounds) if bounds and actual is not None else None
        )
        result["within_prediction"] = (
            bounds[0] <= actual <= bounds[1] if bounds and actual is not None else None
        )
    write_json(args.output, result)
    with args.output.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result))
        writer.writeheader()
        writer.writerow(result)
    rows = [("Before", result["before_seconds"]), ("After", result["after_seconds"])]
    maximum = max(0.001, max((value for _, value in rows if value is not None), default=1))
    chart = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="230" viewBox="0 0 720 230">',
        '<rect width="720" height="230" fill="white"/>',
        f'<text x="24" y="32" font-family="sans-serif" font-size="20">Startup: {html.escape(str(result["scenario"]))}</text>',
    ]
    for index, (label, value) in enumerate(rows):
        y = 65 + index * 55
        chart.append(
            f'<text x="24" y="{y + 20}" font-family="sans-serif" font-size="16">{label}</text>'
        )
        if value is None:
            chart.append(
                f'<text x="120" y="{y + 20}" font-family="sans-serif" font-size="16" fill="#666">Not measured (no successful sample)</text>'
            )
        else:
            width = value / maximum * 430
            chart.append(
                f'<rect x="120" y="{y}" width="{width:.2f}" height="30" fill="{"#697985" if index == 0 else "#26866f"}"/>'
            )
            chart.append(
                f'<text x="{130 + width:.2f}" y="{y + 20}" font-family="sans-serif" font-size="16">{value:.2f} s</text>'
            )
    chart.append(
        '<text x="24" y="210" font-family="sans-serif" font-size="13">Median of successful comparable samples. Missing data is never plotted as zero.</text></svg>'
    )
    args.output.with_suffix(".svg").write_text("\n".join(chart), encoding="utf-8")
    args.output.with_suffix(".md").write_text(
        "# Startup comparison\n\n"
        + "\n".join(
            f"- {key}: {value if value is not None else 'not measured'}"
            for key, value in result.items()
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update(args: argparse.Namespace) -> int:
    """Run the browser update probe with the same independent Compose identity."""
    from dotenv import dotenv_values

    root = args.root.resolve()
    environment = {
        key: value
        for key, value in dotenv_values(args.env_file or root / ".env").items()
        if value is not None
    }
    environment.update(os.environ)
    project = environment.get("COMPOSE_PROJECT_NAME", root.name.lower())
    if not project.endswith("-dev"):
        project += "-dev"
    environment.update(
        COMPOSE_PROJECT_NAME=project,
        COMPOSE_FILE=str(root / "docker-compose.dev.yml"),
        ANIMETTA_IMAGE=f"animetta:{project}",
        ANIMETTA_FRONTEND_IMAGE=f"animetta:{project}-frontend",
    )
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for the update measurement")
    return subprocess.run(
        [
            node,
            str(Path(__file__).resolve().parents[1] / "frontend/scripts/benchmark-startup.mjs"),
            "--root",
            str(root),
            "--mode",
            args.mode,
            "--url",
            args.url,
            "--samples",
            str(args.samples),
            "--output",
            str(args.output.resolve()),
        ],
        env=environment,
        cwd=root,
        check=False,
    ).returncode


def source_snapshot(root: Path) -> dict[str, object]:
    from tooling.quality.fingerprint import is_safe_fingerprint_pattern

    listed = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root
    )
    digest = hashlib.sha256()
    count = 0
    for name in sorted(set(listed.decode("utf-8").split("\0"))):
        if not name or not is_safe_fingerprint_pattern(name):
            continue
        source = root / name
        if not source.is_file():
            continue
        source.resolve().relative_to(root.resolve())
        with source.open("rb") as handle:
            file_digest = hashlib.file_digest(handle, "sha256").digest()
        digest.update(name.encode("utf-8") + b"\0" + file_digest)
        count += 1
    return {
        "file_count": count,
        "sha256": digest.hexdigest(),
        "scope": "tracked and non-ignored untracked files, secrets excluded",
    }


def timed_command(args: argparse.Namespace) -> int:
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    result = subprocess.run(command, check=False)
    write_json(
        args.output,
        {
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "elapsed_seconds": time.perf_counter() - started,
            "exit_code": result.returncode,
        },
    )
    return result.returncode


def worker(args: argparse.Namespace) -> int:
    """Add observation hooks without changing the target's lifecycle decisions."""
    root = args.root.resolve()
    os.chdir(root)
    sys.path[:0] = [str(root), str(root / "src")]
    spec = importlib.util.spec_from_file_location(
        "measured_lifecycle", root / "scripts/runtime_lifecycle.py"
    )
    assert spec and spec.loader
    lifecycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lifecycle)
    from tooling.execution_feedback.lifecycle import LeasedSubprocessBuildDriver

    observations: list[dict[str, object]] = []
    driver = lifecycle._SystemLifecycleDriver
    for method_name in ("run_command", "check_http", "check_logs"):
        original = getattr(driver, method_name)

        def observe(
            self: Any,
            target: str | tuple[str, ...],
            *,
            _method: Any = original,
            _name: str = method_name,
            **kwargs: Any,
        ) -> Any:
            started = time.perf_counter()
            result = _method(self, target, **kwargs)
            observations.append(
                {
                    "kind": _name,
                    "target": list(target) if isinstance(target, tuple) else target,
                    "elapsed_seconds": time.perf_counter() - started,
                    "succeeded": result.succeeded,
                }
            )
            return result

        setattr(driver, method_name, observe)

    original_launch = LeasedSubprocessBuildDriver.launch
    build_timing = args.output.with_name(args.output.stem + "-build.json")

    def launch(self: Any, command: tuple[str, ...], *, log_path: str) -> Any:
        if command[:3] != ("docker", "compose", "build"):
            return original_launch(self, command, log_path=log_path)
        return original_launch(
            self,
            (
                sys.executable,
                str(Path(__file__).resolve()),
                "timed-command",
                "--output",
                str(build_timing),
                "--",
                *command,
            ),
            log_path=log_path,
        )

    setattr(LeasedSubprocessBuildDriver, "launch", launch)

    async def run() -> int:
        windows = 0
        continuation_wait = 0.0
        started = time.perf_counter()
        code = 1
        error = None
        try:
            while True:
                windows += 1
                code = await lifecycle.run_bounded_operation(
                    args.operation,
                    run_id=args.run_id,
                    artifacts_root=args.artifacts_root,
                )
                if code != 2:
                    break
                wait_started = time.perf_counter()
                await asyncio.sleep(1)
                continuation_wait += time.perf_counter() - wait_started
            if code == 0 and args.operation in {"anima-up", "anima-dev"}:
                browser_started = time.perf_counter()
                node = shutil.which("node")
                if node is None:
                    raise RuntimeError("Node.js is required for browser and Socket.IO acceptance")
                base = lifecycle._http_base_url(lifecycle._compose_environment())
                if args.operation == "anima-dev":
                    base = f"http://localhost:{os.environ.get('ANIMETTA_DEV_PORT', '3000')}"
                completed = subprocess.run(
                    [
                        node,
                        str(
                            Path(__file__).resolve().parents[1]
                            / "frontend/scripts/benchmark-startup.mjs"
                        ),
                        "--mode",
                        "surfaces",
                        "--phase",
                        args.phase,
                        "--url",
                        base,
                        "--root",
                        str(root),
                        "--output",
                        str(args.output.with_name(args.output.stem + "-surfaces.json")),
                    ],
                    check=False,
                    timeout=300,
                )
                observations.append(
                    {
                        "kind": "browser",
                        "target": base,
                        "succeeded": completed.returncode == 0,
                        "elapsed_seconds": time.perf_counter() - browser_started,
                    }
                )
                code = completed.returncode
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            code = 1
            error = str(exc)
        payload = {
            "schema_version": 1,
            "run_id": args.run_id,
            "operation": args.operation,
            "exit_code": code,
            "elapsed_seconds": time.perf_counter() - started,
            "feedback_windows": windows,
            "continuation_wait_seconds": continuation_wait,
            "observations": observations,
            "error": error,
            "build": json.loads(build_timing.read_text(encoding="utf-8"))
            if build_timing.exists()
            else None,
        }
        build_log = args.artifacts_root / args.run_id / "animetta-build.log"
        if build_log.is_file():
            payload["build_phases"] = build_phases(
                build_log.read_text(encoding="utf-8", errors="replace")
            )
        if payload["build"]:
            finished = datetime.fromisoformat(payload["build"]["finished_at"])
            payload["build_completion_to_finish_seconds"] = (
                datetime.now(UTC) - finished
            ).total_seconds()
        write_json(args.output, payload)
        return code

    return asyncio.run(run())


def measurement_run_id() -> str:
    # Legacy lifecycle leases repeat this ID in the directory and filename.
    # Keep phase/sample descriptions in metadata, below Windows MAX_PATH here.
    return f"b-{uuid.uuid4().hex[:12]}"


def measure(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    destination = args.output.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    if args.env_file:
        from dotenv import dotenv_values

        for name, value in dotenv_values(args.env_file).items():
            if value is not None:
                environment.setdefault(name, value)
    environment["PYTHONUTF8"] = "1"
    environment["BUILDKIT_PROGRESS"] = "plain"
    for name, value in (
        ("COMPOSE_PROJECT_NAME", args.project),
        ("ANIMETTA_HTTP_PORT", args.http_port),
        ("ANIMETTA_PORT", args.backend_port),
        ("BUILDX_BUILDER", args.builder),
    ):
        if value:
            environment[name] = str(value)
    # Each checkout must have its own image; do not replace the user's live tag.
    if args.project:
        environment["ANIMETTA_IMAGE"] = f"animetta:{args.project}"
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    metadata = {
        "schema_version": 1,
        "phase": args.phase,
        "scenario": args.scenario,
        "revision": revision,
        "root": str(root),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "started_at": datetime.now(UTC).isoformat(),
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "profile": environment.get("ANIMETTA_PROFILE", "production"),
        "project": args.project,
        "samples_requested": args.samples,
        "cold_builder": args.builder,
        "source_snapshot": source_snapshot(root),
        "browser_driver_sha256": hashlib.sha256(
            (
                Path(__file__).resolve().parents[1] / "frontend/scripts/benchmark-startup.mjs"
            ).read_bytes()
        ).hexdigest(),
        "working_diff_sha256": hashlib.sha256(
            subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=root)
        ).hexdigest(),
        "configuration_file_sha256": hashlib.sha256(args.env_file.read_bytes()).hexdigest()
        if args.env_file
        else None,
    }
    write_json(destination / "metadata.json", metadata)
    measurements = []

    def invoke(operation: str, label: str) -> dict[str, Any]:
        result_file = destination / f"{label}.json"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            "--root",
            str(root),
            "--operation",
            operation,
            "--run-id",
            measurement_run_id(),
            "--phase",
            args.phase,
            "--artifacts-root",
            str(destination / "lifecycle"),
            "--output",
            str(result_file),
        ]
        started = time.perf_counter()
        with (destination / f"{label}.log").open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                command,
                cwd=root,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        result = (
            json.loads(result_file.read_text(encoding="utf-8"))
            if result_file.exists()
            else {"exit_code": completed.returncode}
        )
        result["wall_seconds"] = time.perf_counter() - started
        result["sample"] = label
        write_json(result_file, result)
        return result

    if args.scenario == "model-cold":
        for operation in ("anima-down", "host-tts-stop", "host-rvc-stop"):
            if invoke(operation, f"prepare-{operation}")["exit_code"]:
                return 1
    for index in range(1, args.samples + 1):
        if (
            args.scenario == "application"
            and invoke("anima-down", f"prepare-{index:02d}")["exit_code"]
        ):
            return 1
        result = invoke(args.operation, f"sample-{index:02d}")
        measurements.append(result)
        print(json.dumps({"sample": index, "wall_seconds": result["wall_seconds"]}), flush=True)
        if result["exit_code"]:
            break
    times = [item["wall_seconds"] for item in measurements if item["exit_code"] == 0]
    summary = {
        **metadata,
        "samples": measurements,
        "successful_samples": len(times),
        "median_seconds": statistics.median(times) if times else None,
        "min_seconds": min(times) if times else None,
        "max_seconds": max(times) if times else None,
    }
    write_json(destination / "summary.json", summary)
    with (destination / "samples.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "phase",
                "scenario",
                "sample",
                "wall_seconds",
                "exit_code",
                "build_seconds",
                "continuation_wait_seconds",
            ]
        )
        for item in measurements:
            writer.writerow(
                [
                    args.phase,
                    args.scenario,
                    item["sample"],
                    item["wall_seconds"],
                    item["exit_code"],
                    (item.get("build") or {}).get("elapsed_seconds", 0),
                    item.get("continuation_wait_seconds", 0),
                ]
            )
    return 0 if len(times) == args.samples else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    timing = actions.add_parser("timed-command")
    timing.add_argument("--output", type=Path, required=True)
    timing.add_argument("command", nargs=argparse.REMAINDER)
    sample = actions.add_parser("worker")
    for name in ("root", "output", "artifacts-root"):
        sample.add_argument(f"--{name}", type=Path, required=True)
    sample.add_argument("--operation", required=True)
    sample.add_argument("--run-id", required=True)
    sample.add_argument("--phase", choices=("before", "after"), required=True)
    run = actions.add_parser("measure")
    run.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--env-file", type=Path)
    run.add_argument("--phase", choices=("before", "after"), required=True)
    run.add_argument(
        "--scenario", choices=("repeat", "application", "model-cold", "cold-build"), required=True
    )
    run.add_argument("--operation", default="anima-up")
    run.add_argument("--samples", type=int, default=5)
    run.add_argument("--project")
    run.add_argument("--http-port", type=int)
    run.add_argument("--backend-port", type=int)
    run.add_argument("--builder")
    report = actions.add_parser("compare")
    report.add_argument("--before", type=Path)
    report.add_argument("--after", type=Path)
    report.add_argument("--predictions", type=Path)
    report.add_argument("--output", type=Path, required=True)
    updates = actions.add_parser("update")
    updates.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    updates.add_argument("--env-file", type=Path)
    updates.add_argument("--mode", choices=("frontend", "backend"), required=True)
    updates.add_argument("--url", default="http://localhost:3000")
    updates.add_argument("--samples", type=int, default=5)
    updates.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "measure" and (
        args.samples < 1 or (args.scenario == "cold-build" and not args.builder)
    ):
        parser.error("samples must be positive; cold-build requires an isolated --builder")
    if (
        args.action == "measure"
        and args.scenario in {"cold-build", "model-cold"}
        and args.samples != 1
    ):
        parser.error("cold scenarios require --samples 1 and a freshly verified initial state")
    return {
        "timed-command": timed_command,
        "worker": worker,
        "measure": measure,
        "compare": compare,
        "update": update,
    }[args.action](args)


if __name__ == "__main__":
    raise SystemExit(main())
