#!/usr/bin/env python3
"""
Anima performance benchmark suite.

Measures end-to-end latency for the LangGraph pipeline across different
providers and scenarios. Results are written to docs/benchmarks/results.md.

Usage:
    python scripts/benchmark.py quick       # ~2 min (mock providers)
    python scripts/benchmark.py full        # ~10 min (all scenarios)
    python scripts/benchmark.py compare     # compare LLM providers
    python scripts/benchmark.py report      # regenerate report from latest run
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from statistics import median, stdev
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anima.orchestration.graph.orchestrator import LangGraphOrchestratorFactory
from anima.core.service_context import ServiceContext


class Benchmark:
    """Latency benchmark for the Anima LangGraph pipeline."""

    def __init__(self, mode: str = "quick"):
        self.mode = mode
        self.results: Dict[str, Any] = {
            "timestamp": time.time(),
            "mode": mode,
            "scenarios": [],
        }

    async def run_quick(self):
        """Quick benchmark: text E2E with mock providers (10 iterations)."""
        print("Quick benchmark (text E2E, mock providers)...")
        ctx = await self._create_mock_context()
        orch = await LangGraphOrchestratorFactory.create(
            session_id="bench-quick",
            service_context=ctx,
            socketio=None,
            emotion_analyzer=None,
        )

        latencies: List[float] = []
        test_inputs = [
            "你好，请介绍一下你自己。",
            "今天天气怎么样？",
            "帮我搜索一下最近的AI新闻。",
            "你能做什么？",
            "讲个笑话吧。",
        ]

        for i, text in enumerate(test_inputs * 2):  # 10 total
            start = time.perf_counter()
            try:
                await orch.process_text(text=text, user_id="bench", user_name="Bench")
                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)
                print(f"  [{i+1}/10] {elapsed:.0f}ms")
            except Exception as e:
                print(f"  [{i+1}/10] FAILED: {e}")

        self.results["scenarios"].append({
            "name": "text_e2e_mock",
            "iterations": len(latencies),
            "latencies_ms": latencies,
        })
        self._print_summary("text_e2e_mock", latencies)

    async def _create_mock_context(self) -> ServiceContext:
        """Create a ServiceContext with all mock providers."""
        from unittest.mock import MagicMock, AsyncMock
        ctx = MagicMock(spec=ServiceContext)
        ctx.llm_engine = AsyncMock()
        ctx.llm_engine.chat_stream = AsyncMock()
        async def _mock_stream():
            yield "mock response"
        ctx.llm_engine.chat_stream.return_value = _mock_stream()
        ctx.llm_engine.close = AsyncMock()
        ctx.tts_engine = AsyncMock()
        ctx.tts_engine.synthesize = AsyncMock(return_value=b"mock_audio")
        ctx.tts_engine.close = AsyncMock()
        ctx.asr_engine = AsyncMock()
        ctx.asr_engine.transcribe = AsyncMock(return_value="mock transcription")
        ctx.asr_engine.close = AsyncMock()
        ctx.emotion_analyzer = MagicMock()
        ctx.emotion_analyzer.analyze = MagicMock(return_value="neutral")
        ctx.memory_system = AsyncMock()
        ctx.memory_system.retrieve_context = AsyncMock(return_value=[])
        return ctx

    def _print_summary(self, name: str, latencies: List[float]):
        if not latencies:
            print(f"  No valid measurements for {name}")
            return
        latencies.sort()
        p50 = median(latencies)
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        print(f"\n  Results ({name}):")
        print(f"    P50:  {p50:.0f}ms")
        print(f"    P95:  {p95:.0f}ms")
        print(f"    P99:  {p99:.0f}ms")
        print(f"    Min:  {min(latencies):.0f}ms")
        print(f"    Max:  {max(latencies):.0f}ms")
        if len(latencies) > 1:
            print(f"    Std:  {stdev(latencies):.0f}ms")

    async def run_live(self, url: str = "http://localhost:12394", prompts: List[str] = None):
        """Live benchmark: connect to a running server via Socket.IO."""
        if prompts is None:
            prompts = ["你好", "你叫什么名字", "今天过得怎么样？", "1+1等于几？", "讲个笑话吧"]

        print(f"Live benchmark against {url} with {len(prompts)} prompts...")
        try:
            import socketio
        except ImportError:
            print("  ❌ python-socketio not installed. Run: pip install python-socketio")
            return

        sio = socketio.AsyncClient()
        responses = []
        done = asyncio.Event()
        current_chunks = []

        @sio.on("connect")
        async def on_connect():
            print(f"  ✅ Connected")

        @sio.on("sentence")
        async def on_sentence(data):
            if data.get("is_complete"):
                responses.append("".join(current_chunks))
                current_chunks.clear()
                done.set()
            else:
                current_chunks.append(data.get("text", ""))

        @sio.on("audio_with_expression")
        async def on_audio(data):
            if not done.is_set() and not current_chunks:
                done.set()  # audio-only response

        @sio.on("error")
        async def on_error(data):
            print(f"  ❌ Server error: {data}")
            done.set()

        try:
            await sio.connect(url, wait_timeout=10)
        except Exception as e:
            print(f"  ❌ Connection failed: {e}")
            return

        await asyncio.sleep(1)  # let session initialize

        latencies = []
        for i, text in enumerate(prompts, 1):
            done.clear()
            current_chunks.clear()
            start = time.perf_counter()
            await sio.emit("text_input", {"text": text, "user_id": "bench", "from_name": "Bench"})
            try:
                await asyncio.wait_for(done.wait(), timeout=120)
                elapsed = (time.perf_counter() - start) * 1000
                latencies.append(elapsed)
                print(f"  [{i}/{len(prompts)}] {elapsed:.0f}ms | response: {(responses[-1] if responses else '?')[:50]}")
            except asyncio.TimeoutError:
                print(f"  [{i}/{len(prompts)}] TIMEOUT")

        await sio.disconnect()

        if latencies:
            self.results["scenarios"].append({
                "name": "text_e2e_live",
                "iterations": len(latencies),
                "latencies_ms": latencies,
                "server_url": url,
            })
            self._print_summary("text_e2e_live", latencies)

    def save_results(self):
        """Save results to JSON for report generation."""
        output_dir = Path(__file__).parent.parent / "docs" / "benchmarks"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "latest.json"
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to {path}")

    def generate_report(self):
        """Generate markdown report from latest results, augmented with StatsStore data."""
        output_dir = Path(__file__).parent.parent / "docs" / "benchmarks"
        json_path = output_dir / "latest.json"

        lines = [
            f"# Benchmark Results\n",
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.results['timestamp']))}\n",
            f"**Mode:** {self.results['mode']}\n",
            f"\n",
            f"## Summary\n",
            f"\n",
            f"| Scenario | Iterations | P50 | P95 | P99 | Min | Max |\n",
            f"|----------|-----------|-----|-----|-----|-----|-----|\n",
        ]

        for scenario in self.results["scenarios"]:
            latencies = sorted(scenario["latencies_ms"])
            if latencies:
                p50 = median(latencies)
                p95 = latencies[int(len(latencies) * 0.95)]
                p99 = latencies[int(len(latencies) * 0.99)]
                lines.append(
                    f"| {scenario['name']} | {scenario['iterations']} | "
                    f"{p50:.0f}ms | {p95:.0f}ms | {p99:.0f}ms | "
                    f"{min(latencies):.0f}ms | {max(latencies):.0f}ms |\n"
                )

        # ── StatsStore data ──
        try:
            import sqlite3
            db_path = str(Path(__file__).parent.parent / "data" / "stats.db")
            if Path(db_path).exists():
                lines.append("\n## StatsStore Trace Data\n\n")
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row

                # Per-node timing
                cursor = conn.execute("""
                    SELECT node_name, COUNT(*) as cnt, AVG(duration_ms) as avg_ms,
                           MIN(duration_ms) as min_ms, MAX(duration_ms) as max_ms
                    FROM spans WHERE duration_ms IS NOT NULL AND node_name NOT LIKE '%.%'
                    GROUP BY node_name ORDER BY avg_ms DESC
                """)
                rows = cursor.fetchall()
                if rows:
                    lines.append("### Node Timing\n\n")
                    lines.append("| Node | Calls | Avg (ms) | Min | Max |\n")
                    lines.append("|------|-------|----------|-----|-----|\n")
                    for r in rows:
                        lines.append(f"| {r['node_name']} | {r['cnt']} | {r['avg_ms']:.0f} | {r['min_ms']:.0f} | {r['max_ms']:.0f} |\n")
                    lines.append("\n")

                # Sub-node timing
                cursor2 = conn.execute("""
                    SELECT node_name, COUNT(*) as cnt, AVG(duration_ms) as avg_ms
                    FROM spans WHERE duration_ms IS NOT NULL AND node_name LIKE '%.%'
                    GROUP BY node_name ORDER BY avg_ms DESC
                """)
                rows2 = cursor2.fetchall()
                if rows2:
                    lines.append("### Sub-Node Timing\n\n")
                    lines.append("| Step | Calls | Avg (ms) |\n")
                    lines.append("|------|-------|----------|\n")
                    for r in rows2:
                        lines.append(f"| {r['node_name']} | {r['cnt']} | {r['avg_ms']:.0f} |\n")
                    lines.append("\n")

                conn.close()
        except Exception:
            pass

        report_path = output_dir / "results.md"
        with open(report_path, "w") as f:
            f.writelines(lines)
        print(f"Report generated: {report_path}")


# ═══════════════════════════════════════════════════════════════
# Auto Benchmark — Start Real Server → Test → Collect → Report
# ═══════════════════════════════════════════════════════════════

class RealServer:
    """Manages a real Anima server subprocess for benchmarking."""

    DEFAULT_PORT = 12395
    MAX_PORT_TRIES = 5
    START_TIMEOUT = 30  # seconds

    def __init__(self, port: int = None):
        self.port = port or self.DEFAULT_PORT
        self._process = None

    def start(self) -> int:
        """Start uvicorn on a free port. Returns the actual port."""
        for offset in range(self.MAX_PORT_TRIES):
            test_port = self.port + offset
            if self._port_free(test_port):
                self.port = test_port
                break
        else:
            raise RuntimeError(f"Cannot find free port after {self.MAX_PORT_TRIES} tries (tried {self.port}+)")

        import subprocess
        log_path = Path(__file__).parent.parent / "data" / f"benchmark-server-{self.port}.log"
        self._log_file = open(log_path, "w", encoding="utf-8")
        self._process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn",
             "anima.core.socketio_server:get_asgi_app",
             "--host", "127.0.0.1",
             "--port", str(self.port),
             "--log-level", "info"],
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
        )
        return self.port

    async def wait_ready(self) -> bool:
        """Wait until /health returns 200 or timeout."""
        import urllib.request
        deadline = time.monotonic() + self.START_TIMEOUT
        while time.monotonic() < deadline:
            try:
                resp = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2)
                if resp.status == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False

    def stop(self):
        """Terminate the server process."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except Exception:
                self._process.kill()
            self._process = None
        if hasattr(self, "_log_file"):
            self._log_file.close()

    @staticmethod
    def _port_free(port: int) -> bool:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) != 0

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def _validate_env() -> bool:
    """Check if .env has required API keys."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("  ❌ .env file not found")
        return False
    with open(env_path, encoding="utf-8", errors="ignore") as f:
        content = f.read()
    # Check for at least one LLM API key
    found = False
    for key in ("GLM_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY", "LANGFUSE_PUBLIC_KEY"):
        if f"{key}=" in content:
            found = True
            break
    if not found:
        print("  [WARN] No LLM API key found in .env (benchmark will likely fail)")
    else:
        print("  [OK] API keys found in .env")
    return True


async def run_auto():
    """Auto benchmark: start real server → test → collect → report."""
    import atexit

    print(f"\n{'='*60}")
    print("  Anima Auto Benchmark (Real Services)")
    print(f"{'='*60}")

    # 1. Validate
    _validate_env()

    # 2. Start server
    print(f"\n  [1/4] Starting server...")
    server = RealServer()
    port = server.start()
    atexit.register(server.stop)
    print(f"  Server starting on port {port}...")

    ready = await server.wait_ready()
    if not ready:
        server.stop()
        print(f"  ❌ Server failed to start within {RealServer.START_TIMEOUT}s")
        return

    print(f"  ✅ Server ready at http://127.0.0.1:{port}")

    # 3. Run benchmarks
    print(f"\n  [2/4] Running test prompts...")
    url = f"http://127.0.0.1:{port}"

    # Text prompts
    text_prompts = [
        "你好，请介绍一下你自己",
        "今天天气怎么样？",
        "讲个笑话",
        "1+1等于几？",
    ]

    bench = Benchmark()
    await bench.run_live(url=url, prompts=text_prompts)

    # 4. Read StatsStore
    print(f"\n  [3/4] Collecting timing data...")
    await asyncio.sleep(1)  # let async writes flush

    db_path = str(Path(__file__).parent.parent / "data" / "stats.db")
    traces_data = []
    spans_data = []
    otel_spans = []

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Traces
        cur = conn.execute("""
            SELECT total_duration_ms, status, input_type, user_text, created_at
            FROM traces WHERE total_duration_ms IS NOT NULL
            ORDER BY created_at DESC
        """)
        for r in cur.fetchall():
            traces_data.append(dict(r))

        # Spans
        cur2 = conn.execute("""
            SELECT node_name, duration_ms, status
            FROM spans WHERE duration_ms IS NOT NULL AND node_name NOT LIKE '%.%'
        """)
        for r in cur2.fetchall():
            spans_data.append(dict(r))

        # OTel sub-spans
        cur3 = conn.execute("""
            SELECT node_name, duration_ms, status
            FROM spans WHERE duration_ms IS NOT NULL AND node_name LIKE '%.%'
        """)
        for r in cur3.fetchall():
            otel_spans.append(dict(r))

        conn.close()
    except Exception as e:
        print(f"  ⚠️  StatsStore read failed: {e}")

    # 5. Wait for OTel BatchSpanProcessor to flush
    print(f"  [4/4] Waiting for OTel span flush...")
    await asyncio.sleep(6)  # > schedule_delay_millis (5000ms)

    # 6. Stop server
    print(f"  Cleaning up...")
    server.stop()

    # 6. Generate report
    _print_auto_report(bench, traces_data, spans_data, otel_spans)

    # 7. Save results
    runs_dir = Path(__file__).parent.parent / "docs" / "benchmarks" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")

    run_data = {
        "timestamp": ts,
        "mode": "auto",
        "prompts": text_prompts,
        "latencies": bench.results.get("scenarios", []),
        "traces": traces_data,
        "spans": spans_data,
        "otel_spans": otel_spans,
    }

    # Save timestamped
    run_path = runs_dir / f"{ts}.json"
    with open(run_path, "w") as f:
        json.dump(run_data, f, indent=2, ensure_ascii=False)

    # Update latest
    latest_path = runs_dir / "latest.json"
    with open(latest_path, "w") as f:
        json.dump(run_data, f, indent=2, ensure_ascii=False)

    print(f"\n  📄 Run saved: {run_path}")

    # Baseline comparison
    _print_baseline_diff(runs_dir, run_data)

    print(f"\n{'='*60}\n")


def _print_auto_report(bench, traces, spans, otel_spans):
    """Print a structured auto benchmark report."""
    print(f"\n{'='*60}")
    print(f"  🔍 Auto Benchmark Report")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Summary
    latencies = []
    for sc in bench.results.get("scenarios", []):
        latencies.extend(sc.get("latencies_ms", []))
    if latencies:
        latencies.sort()
        print(f"\n  ── End-to-End Latency ──")
        print(f"  Prompts:  {len(latencies)}")
        print(f"  P50:      {latencies[len(latencies)//2]:.0f}ms")
        print(f"  P95:      {latencies[int(len(latencies)*0.95)]:.0f}ms")
        print(f"  P99:      {latencies[int(len(latencies)*0.99)]:.0f}ms")
        print(f"  Avg:      {sum(latencies)/len(latencies):.0f}ms")
        print(f"  Min/Max:  {min(latencies):.0f}ms / {max(latencies):.0f}ms")

    # Node breakdown
    if spans:
        print(f"\n  ── Node Timing ──")
        print(f"  {'Node':25s} {'Calls':>6s} {'Avg(ms)':>8s} {'Min':>8s} {'Max':>8s}")
        print(f"  {'-'*55}")
        by_node = {}
        for s in spans:
            n = s["node_name"]
            if n not in by_node:
                by_node[n] = {"durations": []}
            by_node[n]["durations"].append(s["duration_ms"])
        for name, data in sorted(by_node.items(), key=lambda x: sum(x[1]["durations"])/len(x[1]["durations"]), reverse=True):
            d = data["durations"]
            print(f"  {name:25s} {len(d):>6d} {sum(d)/len(d):>8.0f} {min(d):>8.0f} {max(d):>8.0f}")

    # OTel sub-steps
    if otel_spans:
        print(f"\n  ── Service-Level Spans (OTel) ──")
        print(f"  {'Step':30s} {'Calls':>6s} {'Avg(ms)':>8s}")
        print(f"  {'-'*44}")
        by_step = {}
        for s in otel_spans:
            n = s["node_name"]
            if n not in by_step:
                by_step[n] = {"durations": []}
            by_step[n]["durations"].append(s["duration_ms"])
        for name, data in sorted(by_step.items(), key=lambda x: sum(x[1]["durations"])/len(x[1]["durations"]), reverse=True):
            d = data["durations"]
            print(f"  {name:30s} {len(d):>6d} {sum(d)/len(d):>8.0f}")


def _print_baseline_diff(runs_dir: Path, run_data: dict):
    """Compare current run with previous baseline."""
    latest_path = runs_dir / "latest.json"
    if not latest_path.exists():
        return  # first run, no baseline

    # Read previous (pre-update) latest
    try:
        with open(latest_path) as f:
            old = json.load(f)
        if old.get("timestamp") == run_data.get("timestamp"):
            return  # same run
    except Exception:
        return

    # Compare latencies
    old_lats = []
    for sc in old.get("latencies", old.get("scenarios", [])):
        old_lats.extend(sc.get("latencies_ms", []))
    new_lats = []
    for sc in run_data.get("latencies", run_data.get("scenarios", [])):
        new_lats.extend(sc.get("latencies_ms", []))

    if not old_lats or not new_lats:
        return

    old_lats.sort()
    new_lats.sort()

    def _pct(a, b):
        if b <= 0:
            return 0
        return (a - b) / b * 100

    old_p95 = old_lats[int(len(old_lats) * 0.95)]
    new_p95 = new_lats[int(len(new_lats) * 0.95)]
    delta = _pct(new_p95, old_p95)
    icon = "⚠️" if abs(delta) > 20 else "✅"

    print(f"\n  ── Baseline Comparison ──")
    print(f"  {'Metric':20s} {'Before':>10s} {'After':>10s} {'Δ%':>8s}")
    print(f"  {'-'*48}")
    print(f"  {'P95':20s} {old_p95:>8.0f}ms {new_p95:>8.0f}ms {delta:+7.1f}% {icon}")
    print(f"  {'Avg':20s} {sum(old_lats)/len(old_lats):>8.0f}ms {sum(new_lats)/len(new_lats):>8.0f}ms {_pct(sum(new_lats)/len(new_lats), sum(old_lats)/len(old_lats)):+7.1f}%")

    if abs(delta) > 20:
        print(f"\n  ⚠️  P95 changed by {delta:.0f}% — significant shift detected!")
    else:
        print(f"\n  ✅ P95 stable (Δ={delta:.1f}%)")


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "quick"
    extra_args = sys.argv[2:]

    if mode == "report":
        bench = Benchmark()
        bench.generate_report()
        return

    if mode == "stats":
        """Read StatsStore and print a performance report."""
        import sqlite3
        db_path = str(Path(__file__).parent.parent / "data" / "stats.db")
        if not Path(db_path).exists():
            print(f"StatsDB not found: {db_path}")
            print("Start Anima and run some conversations first.")
            return

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Overview
            cur = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as succ,
                       AVG(total_duration_ms) as avg_dur,
                       MAX(total_duration_ms) as max_dur
                FROM traces WHERE total_duration_ms IS NOT NULL
            """)
            r = cur.fetchone()
            total = r["total"] or 0

            # P95
            cur2 = conn.execute("""
                SELECT total_duration_ms FROM traces
                WHERE status='success' AND total_duration_ms IS NOT NULL
                ORDER BY total_duration_ms
            """)
            durs = [x[0] for x in cur2.fetchall()]

            print(f"\n{'='*60}")
            print("  StatsStore Report")
            print(f"{'='*60}")
            print(f"  Total requests:  {total}")
            print(f"  Success rate:    {r['succ']/total*100:.1f}%" if total > 0 else "  No data")
            if durs:
                print(f"  Avg duration:    {r['avg_dur']:.0f}ms")
                print(f"  Max duration:    {r['max_dur']:.0f}ms")
                print(f"  P50:             {durs[len(durs)//2]:.0f}ms")
                print(f"  P95:             {durs[int(len(durs)*0.95)]:.0f}ms")
                print(f"  P99:             {durs[int(len(durs)*0.99)]:.0f}ms")

            # Per-node
            cur3 = conn.execute("""
                SELECT node_name, COUNT(*) as cnt, AVG(duration_ms) as avg_ms,
                       MIN(duration_ms) as min_ms, MAX(duration_ms) as max_ms
                FROM spans WHERE duration_ms IS NOT NULL AND node_name NOT LIKE '%.%'
                GROUP BY node_name ORDER BY avg_ms DESC
            """)
            rows = cur3.fetchall()
            if rows:
                print(f"\n  ── Node Timing ──")
                for n in rows:
                    print(f"  {n['node_name']:20s}  calls={n['cnt']:4d}  avg={n['avg_ms']:8.0f}ms  min={n['min_ms']:7.0f}ms  max={n['max_ms']:7.0f}ms")

            # Sub-node
            cur4 = conn.execute("""
                SELECT node_name, COUNT(*) as cnt, AVG(duration_ms) as avg_ms
                FROM spans WHERE duration_ms IS NOT NULL AND node_name LIKE '%.%'
                GROUP BY node_name ORDER BY avg_ms DESC
            """)
            rows2 = cur4.fetchall()
            if rows2:
                print(f"\n  ── Sub-Node Timing ──")
                for n in rows2:
                    print(f"  {n['node_name']:25s}  calls={n['cnt']:4d}  avg={n['avg_ms']:8.0f}ms")

            print(f"{'='*60}\n")
        finally:
            conn.close()
        return

    bench = Benchmark(mode)

    if mode == "auto":
        await run_auto()
        return
    elif mode == "diff":
        _run_diff(extra_args)
        return
    elif mode == "quick":
        await bench.run_quick()
    elif mode == "live":
        url = extra_args[0] if extra_args else "http://localhost:12394"
        await bench.run_live(url=url)
    elif mode == "full":
        await bench.run_quick()
        if await _check_server("http://localhost:12394"):
            await bench.run_live(url="http://localhost:12394")
        else:
            print("  (skip live — server not reachable)")
    elif mode == "compare":
        print("Provider comparison not yet implemented")
        await bench.run_quick()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python scripts/benchmark.py [auto|quick|full|compare|report|live|stats|diff]")
        sys.exit(1)

    bench.save_results()
    bench.generate_report()


def _run_diff(args: list):
    """Compare two saved benchmark runs."""
    runs_dir = Path(__file__).parent.parent / "docs" / "benchmarks" / "runs"

    if not args:
        # Show list of available runs
        if not runs_dir.exists():
            print("No benchmark runs found.")
            return
        files = sorted(runs_dir.glob("*.json"))
        # Filter out latest.json
        runs = [f for f in files if f.name != "latest.json"]
        if not runs:
            print("No benchmark runs found. Run `python scripts/benchmark.py auto` first.")
            return
        print(f"\nAvailable runs ({len(runs)}):")
        for r in runs[-10:]:
            sz = r.stat().st_size
            print(f"  {r.stem}  ({sz//1024}KB)")
        print("\nUsage: python scripts/benchmark.py diff <run1> <run2>")
        return

    if len(args) < 2:
        print("Usage: python scripts/benchmark.py diff <run1_timestamp> <run2_timestamp>")
        return

    p1 = runs_dir / f"{args[0]}.json"
    p2 = runs_dir / f"{args[1]}.json"
    if not p1.exists() or not p2.exists():
        print("Run file not found. Check docs/benchmarks/runs/")
        return

    with open(p1) as f:
        r1 = json.load(f)
    with open(p2) as f:
        r2 = json.load(f)

    def _get_lats(data):
        l = []
        for sc in data.get("latencies", data.get("scenarios", [])):
            l.extend(sc.get("latencies_ms", []))
        return sorted(l)

    l1 = _get_lats(r1)
    l2 = _get_lats(r2)

    if not l1 or not l2:
        print("One or both runs have no latency data.")
        return

    def _p(a, b):
        return (a - b) / b * 100 if b else 0

    print(f"\n{'='*60}")
    print(f"  Diff: {args[0]} vs {args[1]}")
    print(f"{'='*60}")
    print(f"  {'Metric':20s} {args[0]:>12s} {args[1]:>12s} {'Δ%':>8s}")
    print(f"  {'-'*52}")
    for pct in [50, 95, 99]:
        v1 = l1[int(len(l1)*pct/100)]
        v2 = l2[int(len(l2)*pct/100)]
        d = _p(v2, v1)
        print(f"  {'P'+str(pct):20s} {v1:>8.0f}ms {v2:>8.0f}ms {d:+7.1f}%")
    print(f"  {'Avg':20s} {sum(l1)/len(l1):>8.0f}ms {sum(l2)/len(l2):>8.0f}ms {_p(sum(l2)/len(l2), sum(l1)/len(l1)):+7.1f}%")

    # Node comparison
    for label, key in [("Spans", "spans"), ("OTel Spans", "otel_spans")]:
        s1 = {s["node_name"]: s["duration_ms"] for s in r1.get(key, [])}
        s2 = {s["node_name"]: s["duration_ms"] for s in r2.get(key, [])}
        if s1 or s2:
            all_keys = sorted(set(list(s1.keys()) + list(s2.keys())))
            print(f"\n  {label}:")
            for k in all_keys:
                v1 = s1.get(k, 0)
                v2 = s2.get(k, 0)
                d = _p(v2, v1) if v1 else 0
                print(f"  {k:25s}  {v1:>8.0f}ms → {v2:<8.0f}ms  {d:+6.1f}%")
    print()


async def _check_server(url: str) -> bool:
    """Check if a server is reachable."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{url}/health", timeout=3)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    asyncio.run(main())
