## 1. Commit Phase 1 + Phase 2 WIP

- [ ] 1.1 Stage all modified files and verify diff doesn't contain debug/test-only changes
- [ ] 1.2 Stage all untracked files in organized groups (handlers, live2d, persistence, data_models, inspection, tests)
- [ ] 1.3 Commit with message: `feat: arch-phase2 — admin_handlers split, Live2D split, StatsStore protocol, data models`
- [ ] 1.4 Archive old OPSX changes: `arch-phase2-refactor-hotspots`, `arch-phase3-engineering-governance`

## 2. Fix get_asgi_app() Duplicate Init

- [ ] 2.1 Add `import threading` to `socketio_server.py`
- [ ] 2.2 Add `_INIT_DONE = threading.Event()` module-level guard
- [ ] 2.3 Add `_INIT_TASKS: list[asyncio.Task] = []` for stale task tracking
- [ ] 2.4 Guard `get_asgi_app()` heavy init with `if not _INIT_DONE.is_set():`
- [ ] 2.5 Cancel stale tasks before re-init
- [ ] 2.6 Track new asyncio tasks (warmup, prewarm, scheduler) in `_INIT_TASKS`
- [ ] 2.7 Set `_INIT_DONE.set()` and `asgi_app` after successful init
- [ ] 2.8 Verify: single set of init logs, no duplicate schedulers

## 3. Fix Type Hints

- [ ] 3.1 `chat_handlers.py`: `admin: "AdminHandlers"` → `admin: "BaseSocketHandler"`
- [ ] 3.2 `bilibili_handlers.py`: `admin: "AdminHandlers"` → `admin: "BaseSocketHandler"`
- [ ] 3.3 `live2d_handlers.py`: `admin: "AdminHandlers"` → `admin: "BaseSocketHandler"`
- [ ] 3.4 Update class/method docstrings to reference `BaseSocketHandler`

## 4. Verification

- [ ] 4.1 Run `mypy src/ --ignore-missing-imports` — no new type errors
- [ ] 4.2 Run `ruff check src/ tests/` — no new lint violations
- [ ] 4.3 Run `PYTHONPATH=src python -m pytest tests/ -v --tb=short -x` — all tests pass
- [ ] 4.4 Start server, confirm single set of startup logs, no duplicate scheduler
