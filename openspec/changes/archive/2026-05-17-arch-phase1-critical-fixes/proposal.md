## Why

Architecture audit revealed critical code quality issues that pose operational risk: **22 locations** swallow exceptions silently (`except Exception: pass`), **13 locations** mix sync/async patterns (`run_until_complete` / `asyncio.run` / `get_event_loop`) risking event loop crashes, and **core business logic** (`services/` at 20% coverage, `utils/` at 0%) is untested. Fixing these now prevents production incidents and enables safe refactoring downstream.

## What Changes

- Eliminate all bare `except Exception: pass` blocks across backend — replace with targeted exception handling + logging
- Refactor sync/async bridge patterns (`run_until_complete`, `asyncio.run`, `run_coroutine_threadsafe`) into fully async code paths
- Add missing test coverage for `services/` (target: 35% → 50%) and `utils/` (target: 0% → 40%)
- No API changes, no breaking changes, no behavioral changes visible to users

## Capabilities

### New Capabilities

*(None — these are internal implementation improvements, not new features)*

### Modified Capabilities

*(None — no spec-level behavior changes. Exception handling and async patterns are implementation details.)*

## Impact

| Area | Impact |
|------|--------|
| `src/anima/services/` | ~20 files affected: add proper exception handling, no behavioral change |
| `src/anima/memory/search/hybrid.py` | 2 swallow points → logging + graceful degradation |
| `src/anima/orchestration/graph/` | `llm_node.py:217`, `stats_handler.py:196,221`, `stats_store.py:72`, `tool_node.py:117,132` — fix swallow patterns |
| `src/anima/core/socketio_server.py` | `run_until_complete` → proper async lifecycle |
| `src/anima/services/live/bilibili_danmaku.py` | sync/async bridge → full async |
| `src/anima/tools/minecraft/tools.py` | sync/async bridge → full async |
| `src/anima/orchestration/graph/stats_handler.py` | `run_coroutine_threadsafe` → full async |
| `src/anima/services/intelligence/llm/langchain_adapter.py` | `asyncio.run()` → proper await |
| `tests/services/` and `tests/utils/` | New test files added |

No dependency changes. No configuration changes. No database migrations.
