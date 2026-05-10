## Why

The Anima project has strong architecture but lacks concrete evidence to prove engineering maturity in interviews. Interviewers ask about performance, reliability, and quality — and "it's solid" isn't an answer. Four targeted enhancements will produce quantitative evidence that elevates the project from "impressive side project" to "production-grade system."

## What Changes

- **Benchmark Report**: Run load tests on the existing benchmark script (`scripts/benchmark.py`), produce a report with QPS, P50/P99 latency, per-node timing breakdown
- **Error Handling Demo**: Demonstrate graceful degradation when LLM times out or rate-limits — mock fallback activates, Dashboard shows error rate curve, session continues without crash
- **Redis Session Sharing**: Move LangGraph checkpoint storage from in-memory to Redis, enabling multi-instance backend and horizontal scalability
- **LLM Evaluation Framework**: Build automated quality evaluation — same prompt across multiple LLMs, semantic similarity scoring, latency/quality tradeoff comparison

## Capabilities

### New Capabilities
- `benchmark-report`: Automated load testing producing QPS, latency distribution, and per-node timing reports. Integrating with existing `scripts/benchmark.py` and StatsStore dashboard.
- `error-resilience`: Graceful degradation path — when LLM/TTS/ASR fail (timeout, rate-limit, network), mock fallback activates, error is logged to StatsStore, session continues. Dashboard shows error rate.
- `redis-session-sharing`: Redis-backed LangGraph checkpoint for multi-instance deployment. Session state persists across backend restarts and is shared between instances.
- `llm-evaluation`: Automated side-by-side LLM comparison — same prompts, semantic similarity scoring, latency/quality metrics. Stores results for A/B analysis.

### Modified Capabilities
<!-- None — these are all new capabilities -->

## Impact

- New files: `scripts/run_benchmark.py`, `scripts/eval_llm.py`, `src/anima/core/redis_checkpoint.py`, `docs/BENCHMARK.md`
- Modified: `orchestration/graph/builder.py` (checkpoint config), `core/socketio_server.py` (Redis init)
- New dependencies: `redis[hiredis]`, `sentence-transformers` (for eval)
- No breaking changes — all new features are additive with feature flags
