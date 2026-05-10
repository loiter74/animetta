## 1. Benchmark Report (Priority 1)

- [x] 1.1 Extend `scripts/benchmark.py` to support `--turns`, `--concurrency`, `--provider`, and `--output` flags
- [x] 1.2 Implement mock-mode benchmark: simulate N conversation turns against mock providers, record per-node latency to StatsStore
- [x] 1.3 Implement concurrency support: `asyncio.gather` with configurable concurrency for throughput measurement
- [x] 1.4 Implement real-provider mode: benchmark against actual LLM API, include token count and cost estimation
- [x] 1.5 Output JSON summary to `docs/benchmarks/runs/<timestamp>.json`
- [x] 1.6 Generate `BENCHMARK.md` from benchmark results with QPS, P50/P95/P99 latency table
- [x] 1.7 Run baseline benchmark (100 turns, mock mode) and commit results

## 2. Error Resilience (Priority 2)

- [x] 2.1 Add configurable timeout to LLM provider calls (default 30s)
- [x] 2.2 Implement catch-and-fallback in `llm_node.py`: on timeout/error, log to StatsStore, switch to mock provider for that turn
- [x] 2.3 Implement catch-and-fallback in `tts_node.py` and `asr_node.py` with same pattern
- [x] 2.4 Add error_type field to StatsStore traces (timeout, rate_limit, network_error, invalid_response)
- [x] 2.5 Add error rate counter to Dashboard KPI cards
- [x] 2.6 Write test: mock LLM timeout → verify fallback activates → verify Dashboard error count increments
- [x] 2.7 Write test: verify fallback is per-turn (next turn uses real provider again)

## 3. Redis Session Sharing (Priority 3)

- [x] 3.1 Add `redis[hiredis]` as optional dependency
- [x] 3.2 Implement `AsyncRedisSaver` in `src/anima/core/redis_checkpoint.py` wrapping LangGraph checkpoint protocol
- [x] 3.3 Add `--redis-url` CLI argument to `socketio_server.py`
- [x] 3.4 Wire Redis checkpoint into `builder.py`: if `--redis-url` present, use `AsyncRedisSaver`, else use `MemorySaver`
- [x] 3.5 Implement Redis unavailable fallback: log warning, use `MemorySaver`
- [x] 3.6 Write test: verify session state persists across server restart with Redis
- [x] 3.7 Write test: verify fallback to MemorySaver when Redis unreachable

## 4. LLM Evaluation Framework (Priority 4)

- [x] 4.1 Add `sentence-transformers` as optional dependency
- [x] 4.2 Create `scripts/eval_llm.py` with `--prompts`, `--providers`, `--reference`, `--output` flags
- [x] 4.3 Implement prompt loading from file (one prompt per line)
- [x] 4.4 Implement parallel LLM querying: send each prompt to all specified providers, record response + latency
- [x] 4.5 Implement semantic similarity scoring using `all-MiniLM-L6-v2` model
- [x] 4.6 Generate output: JSON (`eval_results.json`) + Markdown table (`EVAL.md`) with avg similarity, avg latency, quality/sec
- [x] 4.7 Create sample eval prompt file (`eval_prompts.txt`) with 10 test prompts
- [x] 4.8 Run initial evaluation (DeepSeek vs OpenAI on 10 prompts) and commit results
