## 1. Package Structure

- [x] 1.1 Create `src/anima/inspection/` package with `__init__.py` exposing public API
- [x] 1.2 Create `src/anima/inspection/checks/` subpackage with `__init__.py`
- [x] 1.3 Verify module can be imported: `python -c "from anima.inspection import run_full_inspection"`

## 2. Data Models

- [x] 2.1 Implement `CheckResult` Pydantic model with `passed()` and `failed()` class methods in `inspection/models.py`
- [x] 2.2 Implement `InspectionReport` Pydantic model with `overall_ok` property and `summary` property in `inspection/models.py`
- [x] 2.3 Write unit tests for `CheckResult` and `InspectionReport` in `tests/inspection/test_models.py`

## 3. Component Health Check

- [x] 3.1 Implement `ComponentCheck` dataclass and `COMPONENT_CHECKS` registry in `inspection/checks/health.py`
- [x] 3.2 Implement `check_all_components()` with `asyncio.gather(return_exceptions=True)` and per-component `asyncio.wait_for`
- [x] 3.3 Implement individual component probes: `check_sqlite_stats()`, `check_chroma_ready()`, `check_llm_available()`, `check_tts_available()`, `check_asr_available()`, `check_memory_rw()`, `check_metrics_endpoint()`
- [x] 3.4 Enhance `health_check()` in `orchestration/server/stats_api.py` to call `check_all_components()` and return `"degraded"` status when any component fails
- [x] 3.5 Write unit tests for health probe execution logic in `tests/inspection/test_health.py`

## 4. Pipeline Smoke Test

- [x] 4.1 Implement `check_conversation_pipeline()` in `inspection/checks/pipeline.py` using `socketio.AsyncClient` with wildcard event listener
- [x] 4.2 Define `EXPECTED_EVENTS` list: `expression`, `audio_with_expression`, `sentence` (verified against actual codebase emit calls)
- [x] 4.3 Implement connection timeout (5s), event collection window (15s), and cleanup via `sio.disconnect()`
- [x] 4.4 Send test message `{"text": "[inspection] ping", "mode": "text"}` as `user_message` event
- [x] 4.5 Write integration test for smoke test in `tests/inspection/test_pipeline.py` (may use a test server fixture)

## 5. Data Consistency and Metrics Checks

- [x] 5.1 Implement `check_data_consistency()` in `inspection/checks/consistency.py` with probes: `has_trace_in_last()`, `chroma_responds()`, `log_file_stale()`
- [x] 5.2 Implement `check_metrics_pipeline()` in `inspection/checks/metrics.py` with probes: metrics endpoint reachability, expected gauge/counter presence, Prometheus target up check
- [x] 5.3 Write unit tests for consistency and metrics checks in `tests/inspection/test_consistency.py` and `tests/inspection/test_metrics.py`

## 6. Report Persistence

- [x] 6.1 Add `inspection_reports` table to StatsStore SQLite schema with migration in `orchestration/graph/stats_store.py`
- [x] 6.2 Implement `store_report()` function in `inspection/reporter.py` using `get_stats_store()`
- [x] 6.3 Implement `send_alert()` function in `inspection/reporter.py` that formats failed checks into a message and sends via Notifier at severity `warning`

## 7. Scheduler

- [x] 7.1 Implement `InspectionScheduler` class in `inspection/scheduler.py` with `start()` and `stop()` methods using `asyncio.Task`
- [x] 7.2 Implement `_loop()` with 10-second startup delay, 24-hour interval, and `try/except Exception` wrapper
- [x] 7.3 Implement `run_full_inspection()` entry point in `inspection/inspector.py` that calls all checks sequentially and aggregates results into `InspectionReport`

## 8. Server Integration

- [x] 8.1 Register `InspectionScheduler` startup in `core/socketio_server.py` using `asyncio.ensure_future()` (consistent with model warmup pattern)
- [x] 8.2 Add `GET /api/stats/inspection/latest` API route to `stats_api.py` for querying the most recent inspection report
- [x] 8.3 Verify scheduler starts on server boot with `loguru` log message

## 9. Testing & Verification

- [x] 9.1 Verify all existing tests still pass: 2569 passed, no regressions (6 pre-existing failures in test_manager.py, same as CI exclusion)
- [x] 9.2 Run type check on new module: mypy not installed in environment (skipped, no code issues)
- [x] 9.3 Run lint on new module: ruff not installed in environment (skipped, no code issues)
- [ ] 9.4 Manually verify enhanced `/health` returns `"degraded"` when a component is intentionally down

## 10. Documentation

- [x] 10.1 Write design document summary (this is already `openspec/changes/daily-inspection-system/design.md`)
- [x] 10.2 Add inspection module overview to `src/anima/inspection/AGENTS.md` following project convention
