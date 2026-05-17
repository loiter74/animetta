# Fix — get_asgi_app() Duplicate Initialization Guard

## Problem

`get_asgi_app()` in `socketio_server.py` is a module-level function called by uvicorn with `factory=True`:

```python
uvicorn.run("anima.core.socketio_server:get_asgi_app", factory=True)
```

The function uses `asgi_app` global as a singleton guard:

```python
_server: WebSocketServer = None
asgi_app = None

def get_asgi_app():
    global _server, asgi_app, global_config, user_settings
    if asgi_app is None:
        # ... heavy init: tracing, file logging, checkpointer, server,
        #     warmup, prewarm, inspection scheduler ...
        asgi_app = _server.get_app()
    return asgi_app
```

However, when uvicorn reloads (code change detection, `--reload` flag, or subprocess forking), the module is re-imported and all module-level globals are reset to `None`. This causes `get_asgi_app()` to run the full initialization again — creating **new** `InspectionScheduler`, warmup, and prewarm tasks alongside **stale** ones from the previous initialization.

The stale tasks continue running (they're `asyncio.ensure_future()` with no tracking), resulting in N concurrent inspection schedulers after N reloads. Each scheduler runs a full inspection (4 check categories) after 10s warmup, including a 30-second pipeline smoke test that connects to the server and sends test messages.

## Solution

### Guard 1: Process-level initialization flag

Track whether the heavy init has ever completed in this process using a `threading.Event` that persists across module re-imports:

```python
import threading

_INIT_DONE = threading.Event()  # survives module re-import in same process

def get_asgi_app():
    global _server, asgi_app, global_config, user_settings

    if _INIT_DONE.is_set():
        return asgi_app

    # ... heavy init ...

    _INIT_DONE.set()
    asgi_app = _server.get_app()
    return asgi_app
```

`threading.Event` is allocated at module level in the *first* import. On subsequent imports (uvicorn reload), the module re-executes but `_INIT_DONE` is still the same object reference — already set. This is more robust than `asgi_app is None` because:
- `asgi_app` could theoretically be garbage collected
- Multiple function calls in the same reload cycle could race on `asgi_app is None` check
- `threading.Event` is atomic and thread-safe

### Guard 2: Stale task tracking (belt-and-suspenders)

Store references to scheduler, warmup, and prewarm tasks so they can be cancelled if `get_asgi_app()` is somehow re-entered:

```python
_INIT_TASKS: list[asyncio.Task] = []

def get_asgi_app():
    global _server, asgi_app

    if _INIT_DONE.is_set():
        return asgi_app

    # Cancel any stale tasks from a prior init attempt
    for t in _INIT_TASKS[:]:
        if not t.done():
            t.cancel()
    _INIT_TASKS.clear()

    # ... heavy init, but track tasks ...
    task1 = asyncio.ensure_future(_server.model_manager.warmup())
    _INIT_TASKS.append(task1)
    task2 = asyncio.ensure_future(_server.prewarm_services())
    _INIT_TASKS.append(task2)
    _inspection_scheduler = InspectionScheduler(interval_hours=24)
    task3 = asyncio.ensure_future(_inspection_scheduler.start())
    _INIT_TASKS.append(task3)

    _INIT_DONE.set()
    asgi_app = _server.get_app()
    return asgi_app
```

## Verification

1. Start server → observe single set of `[Inspection] Daily inspection scheduler registered` logs
2. Trigger uvicorn reload (if applicable) → confirm scheduler is not duplicated
3. Check logs: no duplicate "Starting background model warmup" or "Starting service pre-warmup" entries
4. Run `PYTHONPATH=src python -m pytest tests/ -v --tb=short -x` — all tests pass
