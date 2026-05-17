## Why

Server startup logs reveal 5 distinct bugs that degrade system reliability: SQLite thread-safety crashes during meme indexing, inspection pipeline always fails on first run (cold-start timeout), printf-style log format strings silently drop arguments, missing `/metrics` endpoint causes health-check false-negatives, and Chroma collection check confuses "empty" with "unreachable". These are all small, independent fixes — ideal for parallel execution.

## What Changes

- **SQLite thread safety**: Add `check_same_thread=False` + `threading.Lock` to `SQLiteStore` connection. This fixes the `"SQLite objects created in a thread can only be used in that same thread"` crash during `MemePool.maintain_pool()`.
- **Inspection pipeline timeout**: Increase `COLLECTION_DURATION` from 15s to 30s to accommodate cold-start model loading (Faster-Whisper ~20s).
- **Log format string**: Replace printf-style `[%s]` with f-string in `admin_handlers.py:898` to fix silent argument drop.
- **C++-level thread safety for Chroma**: No — Chroma 0-collections check is a false-positive. Adjust inspection logic to treat 0 collections as valid (not a failure).
- **Metrics endpoint**: Add Prometheus `/metrics` ASGI route via `prometheus_client` to eliminate inspection 404 errors.

## Capabilities

### New Capabilities
- `sqlite-thread-safety`: Thread-safe SQLite connection handling for MemoryManager's shared connection
- `prometheus-metrics-endpoint`: Expose `/metrics` HTTP endpoint with Prometheus counters

### Modified Capabilities
- `inspection-pipeline`: Increase collection duration from 15s to 30s; adjust Chroma consistency check to accept 0 collections
- `admin-handlers-logging`: Fix printf-style log format to prevent argument loss

## Impact

- **`src/anima/memory/storage/sqlite.py`**: Add `check_same_thread=False` + `threading.Lock` wrapper
- **`src/anima/memory/system.py`**: No change needed — the `asyncio.to_thread` usage is fine once SQLite is thread-safe
- **`src/anima/inspection/checks/pipeline.py`**: Change `COLLECTION_DURATION` from 15 to 30
- **`src/anima/inspection/checks/consistency.py`**: Allow 0 collections as passing state
- **`src/anima/orchestration/server/handlers/admin_handlers.py`**: Fix format string on line 898
- **`src/anima/core/socketio_server.py`**: Mount Prometheus metrics endpoint
- **`requirements.txt`**: Pin `prometheus_client` dependency
