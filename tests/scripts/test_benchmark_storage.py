"""Measurement failures must never become successful throughput samples."""

from __future__ import annotations

from itertools import count
from pathlib import Path

import pytest

from scripts.benchmark_storage import main, measure_reads


def test_complete_inputs_have_equal_bytes_and_monotonic_samples(tmp_path: Path) -> None:
    first, second = tmp_path / "weight", tmp_path / "index"
    first.write_bytes(b"abc")
    second.write_bytes(b"de")
    ticks = count()
    result = measure_reads(
        [first, second], reader=lambda p: p.stat().st_size, clock=lambda: float(next(ticks))
    )
    assert result["successful_samples"] == 3
    assert [sample["bytes"] for sample in result["samples"]] == [5, 5, 5]
    assert result["median_seconds"] == 5
    assert (
        result["manifest"][0]["sha256"]
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_truncated_read_stops_without_inflating_throughput(tmp_path: Path) -> None:
    path = tmp_path / "weight"
    path.write_bytes(b"abc")
    result = measure_reads([path], reader=lambda _: 2)
    assert result["successful_samples"] == 0
    assert len(result["samples"]) == 1
    assert result["samples"][0]["mib_per_second"] is None
    assert result["median_seconds"] is None


def test_changed_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "weight"
    path.write_bytes(b"abc")

    def change_file(target: Path) -> int:
        target.write_bytes(b"abcd")
        return 3

    result = measure_reads([path], reader=change_file)
    assert result["successful_samples"] == 0
    assert "changed input" in result["samples"][0]["error"]


def test_io_failure_is_saved_and_stops_further_samples(tmp_path: Path) -> None:
    path = tmp_path / "weight"
    path.write_bytes(b"abc")

    def fail(_: Path) -> int:
        raise OSError("unbuffered read unavailable")

    result = measure_reads([path], reader=fail)
    assert result["successful_samples"] == 0
    assert result["samples"][0]["error"] == "unbuffered read unavailable"
    assert len(result["samples"]) == 1


def test_duplicate_file_alias_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "weight"
    path.write_bytes(b"abc")
    with pytest.raises(ValueError, match="Duplicate"):
        measure_reads([path, path.parent / "." / path.name])


def test_empty_input_set_is_rejected() -> None:
    with pytest.raises(ValueError, match="At least"):
        measure_reads([])


def test_cli_preserves_existing_output_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "previous.json"
    output.write_bytes(b"previous evidence")
    monkeypatch.setattr(
        "sys.argv",
        ["benchmark_storage", "--file", str(tmp_path / "missing"), "--output", str(output)],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert output.read_bytes() == b"previous evidence"
