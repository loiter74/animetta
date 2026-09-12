from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from scripts import benchmark_startup
from scripts.check_source_standards import validate_source


def test_measurement_ids_fit_legacy_windows_lease_paths():
    root = PureWindowsPath(
        r"C:\Users\30262\Project\Anima\artifacts\runtime-recovery-20260912"
        r"\before-cold-prepare\lifecycle"
    )
    identifiers = {benchmark_startup.measurement_run_id() for _ in range(20)}
    assert len(identifiers) == 20
    for run_id in identifiers:
        lease = root / run_id / "leases" / f"{run_id}-animetta-build-{'a' * 64}.json"
        temporary = lease.with_suffix(f".json.{'b' * 32}.tmp")
        assert len(str(temporary)) < 260


def test_missing_samples_never_become_zero_seconds_or_fake_improvement():
    assert benchmark_startup.comparison(None, None) == {
        "before_seconds": None,
        "after_seconds": None,
        "seconds_saved": None,
        "reduction_percent": None,
        "speedup": None,
    }
    assert benchmark_startup.comparison({"median_seconds": 60}, None)["reduction_percent"] is None


def test_comparison_reports_savings_speedup_and_rejects_changed_conditions():
    before = {"scenario": "repeat", "driver_sha256": "same", "median_seconds": 60}
    after = {**before, "median_seconds": 12}
    result = benchmark_startup.comparison(before, after)
    assert result["seconds_saved"] == 48
    assert result["reduction_percent"] == 80
    assert result["speedup"] == 5
    with pytest.raises(ValueError, match="driver_sha256"):
        benchmark_startup.comparison(before, {**after, "driver_sha256": "changed"})


def test_timed_command_records_the_command_exit_and_monotonic_elapsed(tmp_path, monkeypatch):
    times = iter([10.0, 12.75])
    monkeypatch.setattr(benchmark_startup.time, "perf_counter", lambda: next(times))
    monkeypatch.setattr(
        benchmark_startup.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 9),
    )
    output = tmp_path / "result.json"
    result = benchmark_startup.timed_command(
        argparse.Namespace(command=["--", "build"], output=output)
    )
    assert result == 9
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["elapsed_seconds"] == 2.75
    assert record["exit_code"] == 9
    assert record["started_at"] and record["finished_at"]


def test_buildkit_phase_durations_keep_cache_and_parallel_steps_separate():
    phases = benchmark_startup.build_phases("""#1 [backend 1/2] RUN uv pip sync
#2 [frontend 1/2] RUN pnpm install
#1 DONE 12.5s
#2 CACHED
#3 exporting to image
#3 DONE 3.7s
""")
    assert [phase["seconds"] for phase in phases] == [12.5, 0, 3.7]
    assert phases[1]["cached"] is True
    assert all("wall_seconds" not in phase for phase in phases)


def test_standard_compose_override_tag_is_valid_but_unknown_tags_are_rejected():
    assert not validate_source(
        PurePosixPath("docker-compose.dev.yml"),
        "services:\n  app:\n    ports: !override [3000:3000]\n",
    )
    assert validate_source(PurePosixPath("ordinary.yml"), "ports: !override []")
    assert validate_source(PurePosixPath("docker-compose.dev.yml"), "ports: !arbitrary []")
