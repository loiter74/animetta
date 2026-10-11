import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import time
from pathlib import Path

repo = Path.cwd()
root = repo / ".zcode/performance/deployment-core-20261011/frontend-build-probe-r2"
assert not root.exists(), "Do not overwrite completed samples"
root.mkdir()
pnpm = shutil.which("pnpm")
assert pnpm
env = os.environ.copy()
env.pop("VITE_EARTH_ENABLED", None)
samples = []
for sample in range(1, 4):
    for mode in ("production", "earth"):
        out = root / f"{mode}-{sample}"
        log = root / f"{mode}-{sample}.log"
        start = time.perf_counter()
        with log.open("wb") as stream:
            completed = subprocess.run([pnpm, "--dir", "frontend", "exec", "vite", "build",
                "--mode", mode, "--outDir", str(out)], env=env, stdout=stream, stderr=subprocess.STDOUT)
        elapsed = time.perf_counter() - start
        assert completed.returncode == 0, log.read_text(encoding="utf-8", errors="replace")[-4000:]
        files = [p for p in out.rglob("*") if p.is_file()]
        cesium = [p for p in files if "cesium" in str(p.relative_to(out)).lower()]
        earth = [p.name for p in files if p.suffix == ".js" and "earth-workspace" in p.read_text(encoding="utf-8")]
        raw = log.read_text(encoding="utf-8", errors="replace")
        samples.append({"mode": mode, "sample": sample, "seconds": elapsed,
            "files": len(files), "bytes": sum(p.stat().st_size for p in files),
            "cesium_files": len(cesium), "cesium_bytes": sum(p.stat().st_size for p in cesium),
            "earth_chunks": earth, "transformed": re.findall(r"(\d+) modules transformed", raw),
            "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
        if mode == "production":
            assert not cesium and not earth, "Optional map resources leaked into core"
        else:
            assert cesium and earth, "Enabled map missing resources"
        print(json.dumps(samples[-1]), flush=True)
summary = {mode: {"median_seconds": statistics.median(x["seconds"] for x in samples if x["mode"] == mode),
    "range_seconds": [min(x["seconds"] for x in samples if x["mode"] == mode),max(x["seconds"] for x in samples if x["mode"] == mode)]}
    for mode in ("production", "earth")}
result = {"node": subprocess.check_output([shutil.which("node"), "--version"], text=True).strip(),
    "pnpm": subprocess.check_output([pnpm, "--dir", "frontend", "--version"], text=True).strip(),
    "conditions": "same dev environment with all packages, alternating modes, warm store, independent output paths", "samples": samples, "summary": summary}
(root / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
