## Context

The Anima startup logs reveal 5 independent bugs spanning storage, inspection, logging, and observability. Each is small and self-contained — no cross-cutting dependencies between fixes. The key design challenge is the SQLite thread-safety fix, which requires understanding the thread boundary created by `asyncio.to_thread(self.meme_pool.maintain_pool)` at `memory/system.py:215`.

### Current state of affected code:
- **SQLiteStore** (`memory/storage/sqlite.py:36`): Uses `sqlite3.connect(db_path)` without `check_same_thread=False`. Connection created on event-loop thread, but `MemePool.maintain_pool()` accesses it from a thread-pool worker.
- **Pipeline inspection** (`inspection/checks/pipeline.py:27`): `COLLECTION_DURATION = 15.0s`. First inspection runs ~10s after server start, before models finish loading (~20s for Faster-Whisper).
- **admin_handlers logging** (`server/handlers/admin_handlers.py:898`): Uses printf-style `"%s"` with positional args, which loguru 0.7.3 on Windows does not interpolate correctly.
- **socketio_server** (`core/socketio_server.py`): No `/metrics` route mounted. OpenTelemetry tracing is initialized but Prometheus exporter is not wired.
- **Consistency check** (`inspection/checks/consistency.py:66`): Treats `len(collections) == 0` as reachable but `check_data_consistency()` doesn't distinguish 0-collections from connection failures.

## Goals / Non-Goals

**Goals:**
1. Make `SQLiteStore` connection safe for cross-thread access from `asyncio.to_thread`
2. Raise inspection pipeline timeout so cold-start passes
3. Fix printf-style log format so all arguments appear in output
4. Expose Prometheus `/metrics` endpoint on the ASGI server
5. Make Chroma 0-collections pass as a valid state in data consistency check

**Non-Goals:**
- Not making `MemePool.maintain_pool()` async (would require propagating async through all callers)
- Not adding full OpenTelemetry-Prometheus bridge (just a standalone `/metrics` endpoint)
- Not fixing Minecraft bot connection or MCP Docker startup (environment-dependent)

## Decisions

### Decision 1: SQLite thread safety — `check_same_thread=False` + `threading.Lock`
**Choice**: Add `check_same_thread=False` to `sqlite3.connect()` and wrap all `self.conn` access with a `threading.Lock`.
**Rationale**: `check_same_thread=False` allows the connection to be used from the thread-pool worker where `maintain_pool()` runs. The `threading.Lock` prevents concurrent writes from both the event-loop thread (via `store_turn` -> `ingest_turn` -> `_index_file`) and the thread-pool worker. Alternatives considered:
- *Make `maintain_pool` async* → requires rewriting `MemePool` methods and all callers, large blast radius.
- *Create per-thread connections* → over-engineering for a single known thread boundary.
- *Remove `asyncio.to_thread` wrapper* → blocks event loop during synchronous `maintain_pool` execution.

### Decision 2: Inspection timeout — raise COLLECTION_DURATION to 30s
**Choice**: Increase from 15s to 30s.
**Rationale**: 30s is the minimum window to accommodate all model cold-start latencies: Faster-Whisper ~20s, GPT-SoVITS ~5s, first LLM call ~5-8s. 15s is demonstrably insufficient (pipeline gets `connection-established` + `control/conversation-start` but nothing else).

### Decision 3: Log format — f-string replacement
**Choice**: Replace `"[%s] ... %d ... %d"` with `f"[{sid}] ... {len(active)} ... {len(pending)}"`.
**Rationale**: Codebase uniformly uses f-strings for log formatting (see line 876 in same function). The printf-style `%s`/`%d` with positional args is the only such usage and loguru 0.7.3 on Windows doesn't interpolate it.

### Decision 4: Metrics — standalone Prometheus endpoint
**Choice**: Add `prometheus_client` ASGI app mounted via `Starlette.mount()` or use `prometheus_fastapi_instrumentator`.
**Rationale**: Minimal code change. Mount a simple ASGI `make_asgi_app()` from `prometheus_client` at the existing server port. Avoids adding a separate metrics port or restructuring the ASGI app.

### Decision 5: Chroma 0-collections — adjust inspection logic
**Choice**: In `consistency.py`, change `chroma_responds()` to return `True` when 0 collections are found (Chroma is reachable, just empty).
**Rationale**: 0 collections on first startup is expected behavior. The check should return `True` as long as Chroma responds without error. Only return `False` on exceptions.

## Risks / Trade-offs

- **[SQLite Lock contention]** The `threading.Lock` could become a bottleneck if both the event-loop and thread-pool frequently write to SQLite. → **Mitigation**: `maintain_pool` runs hourly, `store_turn` runs per conversation. Contention is negligible.
- **[Metrics endpoint overhead]** Adding Prometheus metrics on the same ASGI server adds minimal overhead (~1µs per request for counter increments). → **Mitigation**: Use `DISABLE_PROMETHEUS` env var for disabling in dev.
- **[30s inspection wait]** Changes first-inspection latency from ~16s to ~31s. → **Mitigation**: This only affects the first inspection after server start (subsequent runs happen 24h later on a warm system and complete in ~2s).
