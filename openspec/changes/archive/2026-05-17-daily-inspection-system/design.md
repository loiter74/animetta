## Context

Anima has mature reactive monitoring: 4 Grafana dashboards, 5 Prometheus alert rules, 16 OTel instruments, and a StatsStore SQLite for trace persistence. It has 2500+ unit tests at 34% coverage. But there is zero **proactive** end-to-end verification of the running system. Common bug patterns from the last 2 months include: VAD pipeline races (10 fixes), SQLite deadlocks (5 fixes), WebSocket initialization ordering, and frontend transcript duplication.

The `/health` endpoint (`stats_api.py:117`) returns `{"status":"ok"}` regardless of whether the LLM model is loaded, the Chroma database is reachable, or the WebSocket event pipeline is functional. The observability stack (OTel Collector → Prometheus → Grafana) catches metric anomalies but does not simulate user flows.

## Goals / Non-Goals

**Goals:**
- Upgrade `/health` to return per-component pass/fail status with granular diagnostics
- Implement an end-to-end pipeline smoke test using a real Socket.IO client
- Add a daily scheduled inspection runner with structured reports and alert integration
- Verify data layer health (StatsStore SQLite traces, Chroma reachability, log file freshness, Prometheus metrics endpoint)
- Follow existing project conventions (Pydantic V2, asyncio, loguru, `asyncio.ensure_future` lifecycle pattern)

**Non-Goals:**
- Not a test framework replacement — does not use pytest/mock; real system only
- Not a replacement for Prometheus alert rules — complementary proactive verification, not reactive monitoring
- Not a load/stress testing tool — single-request verification, no concurrency testing
- Not a replacement for log analysis — does not parse or interpret log content beyond file freshness
- Not a debugging tool — reports pass/fail, does not suggest fixes

## Decisions

### 1. Module placement: `src/anima/inspection/` (independent package)

**Chose `src/anima/inspection/`** over placing checks inside `orchestration/`, `utils/`, or `tests/`.

| Alternative | Rejected Because |
|-------------|-----------------|
| `orchestration/` | Inspection is not a LangGraph node; it does not process user requests. Co-locating would confuse the boundary between runtime processing and offline verification. |
| `utils/` | Inspection is stateful (scheduler loop, report persistence) and has its own data models. Utils are stateless helpers. |
| `tests/` | Tests use pytest + mock fixtures and run at build time. Inspection uses real clients and runs at runtime. Mixing them creates a confusing dual-purpose directory. |

The new package owns: scheduler lifecycle, check implementations, report generation, and data models. It depends on (does not modify): `orchestration.server` (Socket.IO events, StatsStore), `notifier` (alert delivery), `memory/system.py` (Chroma probing).

### 2. Health check: concurrent async probes with independent timeouts

**Chose `asyncio.gather(return_exceptions=True)` with per-component `asyncio.wait_for`** over sequential execution or a global timeout.

Rationale: Sequential checks mean one hung component (e.g., LLM API timeout at 30s) blocks all subsequent checks. A global timeout means if LLM hangs, you get no TTS/Chroma/ASR status. Independent timeouts + `return_exceptions=True` ensures every component reports its status regardless of any other component's failure. The `/health` response is guaranteed within max(<all timeouts>) ≈ 5 seconds.

### 3. Pipeline smoke test: real Socket.IO client, not HTTP or pytest

**Chose `socketio.AsyncClient`** over `curl` HTTP calls or pytest fixtures.

Socket.IO is the primary user-facing protocol. If WebSocket routing breaks but HTTP REST works, an HTTP smoke test would report green. `socketio.AsyncClient` exercises the exact same code path as a real user: connection → `user_message` emission → event collection across all 7 LangGraph nodes → disconnection.

Event collection uses `@sio.on("*")` (wildcard listener) rather than explicit event handlers. Rationale: wildcard capture records all events, including unexpected ones. This provides richer diagnostic data — if a new event appears (e.g., `rag_cache_hit`) that the check doesn't expect, the report shows it rather than silently ignoring it.

### 4. Scheduler: `asyncio.ensure_future()` in server startup

**Chose `asyncio.ensure_future()` in `socketio_server.py`** over external cron, systemd timer, or a Starlette lifespan context manager.

Rationale:
- **Over external cron**: Inspection lifecycle should match server lifecycle. If the server is down, Prometheus already alerts via `up{job="anima"}==0`. An external cron would report failures for a known-down service, creating noise. When the server restarts, inspection should recover automatically — `asyncio.Task` achieves this; cron requires separate monitoring.
- **Over Starlette `lifespan`**: The project does not use Starlette's lifespan pattern; it uses `asyncio.ensure_future()` for background tasks (model warmup, service pre-warming). Consistency with existing patterns reduces cognitive overhead.

The scheduler includes a 10-second startup delay to let services warm up before the first inspection, avoiding false negatives during model loading.

### 5. Report persistence: StatsStore SQLite

**Chose StatsStore (existing)** over a new SQLite instance, file-based JSON, or in-memory-only.

StatsStore already manages SQLite for traces/spans with migration support. Adding an `inspection_reports` table is a natural extension. File-based JSON would require separate I/O management and lack query capability. In-memory-only means reports are lost on restart, defeating the purpose of trend analysis.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Smoke test messages pollute conversation history** | Messages include `[inspection]` prefix; Memory middleware filters them out of context injection |
| **Smoke test adds LLM/TTS cost (~$0.001/day)** | Negligible cost. Single short message ("ping") to lowest-cost provider |
| **Smoke test fails during deployment/restart** | Scheduler delays 10s after startup; check failures during known restart windows are expected and non-actionable |
| **Chroma/SQLite probes add marginal I/O** | Checks are lightweight (single-row queries). No measurable impact on production latency |
| **`asyncio.Task` crash stops all future inspections** | `try/except` in the outer loop catches all exceptions; individual inspection failures do not kill the loop |
| **Inspection scheduler leaks resources if server is improperly shut down** | Task cancellation is non-critical — the task sleeps 24h between runs. On server restart, a new task is created |

## Open Questions

- Should the inspection interval be configurable via `config/app.py` or a YAML file, or hardcoded to 24h initially? (Recommendation: hardcode 24h for MVP, add config later.)
- Should failed inspections auto-trigger a re-run (e.g., retry 2x with 5min delay) or just alert on first failure? (Recommendation: alert on first failure; retry logic adds complexity without clear benefit at this stage.)
- Should inspection reports include a "trend" section comparing against the past N runs? (Recommendation: defer to post-MVP; requires report history query capability.)
