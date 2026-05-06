## 1. Server Lifecycle

- [x] 1.1 Implement `RealServer` class: spawn uvicorn subprocess on a free port, wait for /health, kill on exit
- [x] 1.2 Add environment validation: check .env for required API keys before starting
- [x] 1.3 Add port selection: start at 12395, increment if busy, with configurable override

## 2. Benchmark Client

- [x] 2.1 Implement text benchmark in `run_auto()`: connect via Socket.IO, send N prompts, collect response latencies
- [~] 2.2 Audio benchmark: wired, needs `benchmark_data/test_audio.wav` for full test
- [~] 2.3 Audio test data: create `scripts/benchmark_data/test_audio.wav` (pending)
- [x] 2.4 Wire text prompts into sequential auto flow

## 3. StatsCollector

- [x] 3.1 Implement StatsStore reading in `run_auto()`: traces + spans + otel_spans
- [x] 3.2 OTel span aggregation: grouped by node_name with avg/min/max/count
- [x] 3.3 Data filtered by benchmark window (reads current DB)

## 4. Report Generator

- [x] 4.1 Structured console report with KPI + per-node breakdown
- [x] 4.2 Baseline comparison: load runs/latest.json, compute delta%
- [x] 4.3 Regression detection: P95 change >20% → ⚠️ flag
- [x] 4.4 OTel sub-step breakdown table (llm.api_call, tts.synthesize, etc.)

## 5. Result Persistence

- [x] 5.1 Save run to `docs/benchmarks/runs/<timestamp>.json`
- [x] 5.2 Update `docs/benchmarks/runs/latest.json` after each run
- [x] 5.3 Add `diff` subcommand: compare any two saved runs

## 6. Integration & Verification

- [x] 6.1 Wire `auto` command into benchmark.py main()
- [~] 6.2 `--dry-run` flag (config validation separate from server start)
- [~] 6.3 End-to-end verification (requires API keys + running the command)
