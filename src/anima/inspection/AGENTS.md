# INSPECTION — DAILY SYSTEM VERIFICATION

**Generated:** 2026-05-17

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW

Proactive end-to-end inspection system that verifies the Anima backend is healthy. Runs 4 check categories daily on a background asyncio.Task, persists results to SQLite, and sends alerts via NotifierManager on failures. 6 files total.

## STRUCTURE

```
inspection/
├── models.py             # CheckResult + InspectionReport (Pydantic V2, frozen)
├── inspector.py          # run_full_inspection() — aggregates 4 checks
├── scheduler.py          # InspectionScheduler — background asyncio.Task
├── reporter.py           # store_report() + send_alert() — persistence & alerting
├── checks/               # Individual verification probes
│   ├── health.py         # Component health (LLM/TTS/ASR/Chroma/StatsStore)
│   ├── pipeline.py       # End-to-end Socket.IO conversation smoke test
│   ├── consistency.py    # Data layer health (traces, Chroma, log files)
│   └── metrics.py        # Prometheus /metrics endpoint self-check
└── AGENTS.md             # This file
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add a new check | `checks/` | Return `CheckResult`; register in `checks/__init__.py` |
| Change check schedule | `scheduler.py` | `interval_hours` parameter |
| Change alert format | `reporter.py` | `send_alert()` builds Alertmanager v4 payload |
| Query latest report | `orchestration/server/stats_api.py` | `GET /api/stats/inspection/latest` |
| Persistence backend | `orchestration/graph/stats_store.py` | `inspection_reports` table |

## KEY PATTERNS

- **Check function signature**: `async def check_xxx() -> CheckResult`
- **Check naming**: `category/subcategory` (e.g., `pipeline/conversation`, `metrics_pipeline`)
- **Crash safety**: Each check in `run_full_inspection()` is wrapped in `try/except` — one crash never aborts others
- **Frozen models**: `CheckResult` and `InspectionReport` use `ConfigDict(frozen=True)` — construct all data before creating the model
- **Reporter flow**: `store_report()` → StatsStore SQLite; `send_alert()` → NotifierManager (Alertmanager v4 format)
- **Scheduler lifecycle**: `start()` creates asyncio.Task → sleep 10s warmup → infinite loop → `stop()` signals event

## ANTI-PATTERNS

- ❌ Never mutate frozen Pydantic models after construction — gather all data first, then create the model
- ❌ Never let a single check crash abort the full inspection — use try/except per check in `run_full_inspection()`
- ❌ Never block server startup on inspection scheduler — gate with try/except in socketio_server.py
- ❌ Never hardcode the NotifierManager dependency — always handle the case where it is not configured
- ❌ Do not modify existing check implementations (health.py, pipeline.py, consistency.py, metrics.py) when adding new ones

## NOTES

- The scheduler uses a 10-second warmup delay to let the server finish initializing before the first run.
- `store_report()` serializes checks to JSON via `model_dump()` before persisting to SQLite.
- `get_latest_inspection_report()` returns a dict with `checks` as a deserialized dict, not CheckResult objects.
- The API route returns 404 if no reports exist yet — the scheduler runs its first inspection after warmup.
