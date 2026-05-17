## Why

Anima has mature reactive monitoring (Prometheus alerts, Grafana dashboards, OTel tracing) and 2500+ unit tests, but **zero proactive end-to-end verification**. When components silently degrade—LLM API key expires, Chroma process dies, WebSocket routing breaks mid-refactor—there's no automated check catching it before users do. Common bug patterns (SQLite deadlocks, VAD pipeline races, frontend transcript duplication) go undetected for hours or days because the system's "everything is fine" metric masks partial failures.

## What Changes

- **Enhanced `/health` endpoint**: Upgraded from binary liveness (`{"status":"ok"}`) to per-component health checks (LLM, TTS, ASR, Chroma, StatsStore, Memory, log file) with concurrent async probes and independent timeouts.
- **Pipeline smoke test**: Uses a real `socketio.AsyncClient` to initiate a full conversation (text→7 LangGraph nodes→Live2D events→TTS audio→transcript), verifying the critical user path end-to-end in the running system.
- **Daily inspection scheduler**: An `asyncio.Task` registered in the FastAPI lifespan that runs full inspection daily, generates structured `InspectionReport` records, stores results to StatsStore, and pushes failures through the existing Notifier alert pipeline (Discord/Feishu/Email).
- **Data consistency & metrics pipeline checks**: Verifies StatsStore SQLite has recent traces, Chroma is queryable, log files are being written, and the Prometheus `/metrics` endpoint is reachable and contains expected gauge/counter names.

## Capabilities

### New Capabilities

- `component-health-check`: Per-component async health probes with independent timeouts, returning granular pass/fail status for each service dependency (LLM, TTS, ASR, Chroma, StatsStore, Memory, log file, Prometheus metrics endpoint). Exposed via enhanced `GET /health` endpoint and internal inspection API.
- `pipeline-smoke-test`: End-to-end conversation pipeline verification using a real Socket.IO client to send a test message, collect expected events across all 7 LangGraph nodes (emotion_update, tts_audio_data, transcript_complete), and report missing/unexpected events with timing data.
- `inspection-scheduler`: Scheduled daily inspection runner. Defines the `InspectionReport` and `CheckResult` data models, the `run_full_inspection()` entry point, the background `asyncio.Task` lifecycle, report persistence to StatsStore, and failure notification via the existing Notifier.

### Modified Capabilities

None—no existing spec-level requirements are changing. The enhanced `/health` endpoint is an additive behavior on the existing `stats_api.py` route; no breaking changes to the response schema.

## Impact

- **New module**: `src/anima/inspection/` — independent package with scheduler, inspector, checks (health/pipeline/consistency/metrics), reporter, models. No modification to existing orchestration or service modules.
- **Modified files**: `src/anima/orchestration/server/stats_api.py` (enhanced `/health` endpoint), `src/anima/core/socketio_server.py` (register inspection scheduler in lifespan).
- **New dependency**: `python-socketio[asyncio_client]` already exists in project as dev dependency; may need to uplift to production dependency for pipeline smoke test client.
- **No breaking changes**. Existing `/health` response format preserved; new `checks` field is additive. All inspection logic is opt-in (scheduler starts automatically but can be disabled via config).
- **Cost**: Pipeline smoke test sends 1 short LLM message per day (~$0.001). All other checks are zero-cost (local probes).
