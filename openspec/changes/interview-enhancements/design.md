## Context

Four independent enhancements targeting interview preparedness. Each is additive, requires no breaking changes, and can be implemented in any order. All leverage existing infrastructure (StatsStore, ServicePool, LangGraph checkpoint).

## Goals / Non-Goals

**Goals:**
- Produce quantitative performance data (benchmark report)
- Demonstrate graceful failure handling (error resilience)
- Enable horizontal scalability (Redis session sharing)
- Enable data-driven LLM selection (evaluation framework)

**Non-Goals:**
- Not productionizing the entire system (Redis is for demo, not full cluster)
- Not building a CI-integrated eval pipeline (manual runs are sufficient)
- Not changing the core graph structure for any of these

## Decisions

### D1: Benchmark — Extend existing script, output to StatsStore
- **Decision**: Extend `scripts/benchmark.py`, push results to StatsStore SQLite, display on existing Dashboard
- **Why**: No new UI needed. StatsStore already has the schema. Dashboard already has latency charts.
- **Alternative**: Standalone `BENCHMARK.md` file — simpler but less impressive in demo. Choose integrated approach for live dashboard display.

### D2: Error Resilience — Mock fallback pattern, not retry logic
- **Decision**: When LLM/TTS/ASR fail after 1 attempt → switch to mock provider → log error to StatsStore → continue session
- **Why**: Retry logic adds complexity without guaranteed success. Mock fallback is deterministic and demonstrates graceful degradation.
- **Alternative**: Exponential backoff retry → more "production", but harder to demo (no visible error curve on Dashboard). Mock fallback is more impressive in interview.

### D3: Redis — Feature flag, fall back to in-memory
- **Decision**: `--redis-url` CLI flag. If absent, use existing MemorySaver. If present, use `AsyncRedisSaver`.
- **Why**: Zero impact on existing users. Interview demo uses flag to show multi-instance capability.
- **Alternative**: Always Redis → adds mandatory dependency, breaks local-first experience. Feature flag is safer.

### D4: LLM Eval — CLI script, semantic similarity scoring
- **Decision**: Python script `scripts/eval_llm.py` that sends same prompts to multiple LLMs, scores via `sentence-transformers` cosine similarity. Outputs JSON + Markdown table.
- **Why**: Minimal dependency (sentence-transformers is lightweight). Manual execution is sufficient for interview prep.
- **Alternative**: Web UI eval dashboard → overengineered for the goal. CLI script with Markdown output is enough.

## Risks / Trade-offs

- [Risk] `redis[hiredis]` adds native dependency that may fail on Windows → Mitigation: make Redis entirely optional via feature flag
- [Risk] `sentence-transformers` may download large model on first run → Mitigation: document model size, add `--model` flag for lightweight alternatives
- [Risk] Benchmark may reveal poor performance → Mitigation: that's the point — baseline data is better than no data
