"""Read model files without Windows file caching; never claim model load latency."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import statistics
import time
from collections.abc import Callable, Sequence
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def read_unbuffered(path: Path, chunk_bytes: int = 1024 * 1024) -> int:
    """Read an entire regular file with FILE_FLAG_NO_BUFFERING and aligned memory."""
    if os.name != "nt":
        raise OSError("Unbuffered storage measurement requires Windows")
    if chunk_bytes <= 0 or chunk_bytes % 65536:
        raise ValueError("chunk_bytes must be a positive multiple of 65536")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    kernel.ReadFile.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.VirtualAlloc.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    kernel.VirtualAlloc.restype = ctypes.c_void_p
    kernel.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    kernel.VirtualFree.restype = wintypes.BOOL
    # No write sharing: an active writer must not change a timed input.
    handle = kernel.CreateFileW(str(path.resolve()), 0x80000000, 1, None, 3, 0x28000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = None
    try:
        # VirtualAlloc returns allocation-granularity aligned memory (64 KiB).
        buffer = kernel.VirtualAlloc(None, chunk_bytes, 0x3000, 0x04)
        if not buffer:
            raise ctypes.WinError(ctypes.get_last_error())
        total = 0
        count = wintypes.DWORD()
        while True:
            if not kernel.ReadFile(handle, buffer, chunk_bytes, ctypes.byref(count), None):
                raise ctypes.WinError(ctypes.get_last_error())
            total += count.value
            if count.value < chunk_bytes:
                return total
    finally:
        if buffer:
            kernel.VirtualFree(buffer, 0, 0x8000)
        kernel.CloseHandle(handle)


def measure_reads(
    paths: Sequence[Path],
    *,
    samples: int = 3,
    reader: Callable[[Path], int] = read_unbuffered,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Measure complete equal input sets, retaining failures without success statistics."""
    if samples < 1 or not paths:
        raise ValueError("At least one file and one sample are required")
    resolved = [path.resolve(strict=True) for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Duplicate input files would count bytes more than once")
    if any(not path.is_file() for path in resolved):
        raise ValueError("Inputs must be regular files")
    manifest: list[dict[str, Any]] = []
    for path in resolved:
        stat = path.stat()
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        manifest.append(
            {
                "path": str(path),
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": digest,
            }
        )
    if not sum(item["bytes"] for item in manifest):
        raise ValueError("The input set contains no bytes")
    records: list[dict[str, Any]] = []
    for index in range(samples):
        record: dict[str, Any] = {"sample": index + 1, "files": [], "succeeded": False}
        started = clock()
        try:
            for path, item in zip(resolved, manifest, strict=True):
                stat = path.stat()
                if (stat.st_size, stat.st_mtime_ns) != (item["bytes"], item["mtime_ns"]):
                    raise ValueError(f"Input changed before reading: {path.name}")
                read_started = clock()
                count = reader(path)
                elapsed = clock() - read_started
                stat = path.stat()
                if count != item["bytes"] or (stat.st_size, stat.st_mtime_ns) != (
                    item["bytes"],
                    item["mtime_ns"],
                ):
                    raise ValueError(f"Incomplete or changed input: {path.name}")
                record["files"].append({"path": str(path), "bytes": count, "seconds": elapsed})
            record["succeeded"] = True
        except (OSError, ValueError) as exc:
            record["error"] = str(exc)
        record["seconds"] = clock() - started
        record["bytes"] = sum(item["bytes"] for item in record["files"])
        record["mib_per_second"] = (
            record["bytes"] / 1024**2 / record["seconds"]
            if record["succeeded"] and record["seconds"] > 0
            else None
        )
        records.append(record)
        if not record["succeeded"]:
            break
    elapsed_values = [item["seconds"] for item in records if item["succeeded"]]
    return {
        "schema_version": 1,
        "metric": "windows_unbuffered_file_read",
        "recorded_at": datetime.now(UTC).isoformat(),
        "cache_contract": "FILE_FLAG_NO_BUFFERING bypasses Windows file cache; device cache is not flushed. Hashing occurs before timing. This is not model loading or guaranteed physical cold reading.",
        "manifest": manifest,
        "samples_requested": samples,
        "samples": records,
        "successful_samples": len(elapsed_values),
        "median_seconds": statistics.median(elapsed_values) if elapsed_values else None,
        "min_seconds": min(elapsed_values) if elapsed_values else None,
        "max_seconds": max(elapsed_values) if elapsed_values else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, action="append", required=True)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Resolve output first so it can never overwrite one of the model inputs.
    if args.output.resolve() in {path.resolve() for path in args.file}:
        parser.error("Output must not overwrite an input file")
    if args.output.exists():
        parser.error("Output must be a new file; existing evidence is preserved")
    result = measure_reads(args.file, samples=args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps({"output": str(args.output), "successful_samples": result["successful_samples"]})
    )
    return 0 if result["successful_samples"] == args.samples else 1


if __name__ == "__main__":
    raise SystemExit(main())
