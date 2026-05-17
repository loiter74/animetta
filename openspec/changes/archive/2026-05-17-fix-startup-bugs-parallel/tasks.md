## 1. SQLite Thread Safety (parallel agent)

- [x] 1.1 Add `check_same_thread=False` to `sqlite3.connect()` in `storage/sqlite.py:36`
- [x] 1.2 Add `import threading` and `self._lock = threading.RLock()` to `SQLiteStore.__init__()`
- [x] 1.3 Wrap all `self.conn.execute()` and `self.conn.commit()` calls in `SQLiteStore` public methods with `with self._lock:`
- [x] 1.4 Syntax verified via `python -m py_compile` (LSP not available)
- [x] 1.5 269 meme/memory tests passed, 610 broader tests passed

## 2. Inspection Pipeline Timeout (parallel agent)

- [x] 2.1 Change `COLLECTION_DURATION` from `15.0` to `30.0` in `inspection/checks/pipeline.py:27`
- [x] 2.2 Comment updated to reflect 30s collection duration
- [x] 2.3 Syntax verified via `python -m py_compile`

## 3. Chroma 0-Collections Fix (parallel agent)

- [x] 3.1 Improved chroma_responds() log message to clarify "reachable with N collection(s)" instead of "reachable: N collections"
- [x] 3.2 Syntax verified via `python -m py_compile`

## 4. Admin Handlers Log Format Fix (parallel agent)

- [x] 4.1 Replaced printf-style `"[%s] ... %d ... %d"` with f-string in `admin_handlers.py:898`
- [x] 4.2 Syntax verified via `python -m py_compile`

## 5. Prometheus Metrics Endpoint (parallel agent)

- [x] 5.1 Added `prometheus-client>=0.19.0` to `requirements.txt`
- [x] 5.2 Mounted `make_asgi_app()` at `/metrics` in `websocket.py` (not socketio_server.py — the ASGI app lives in WebSocketServer)
- [x] 5.3 Syntax verified via `python -m py_compile`
- [x] 5.4 Prometheus client import verified: `python -c "from prometheus_client import make_asgi_app; print('OK')"`
