## Context

Architecture audit of the Anima codebase identified three critical code quality issues:

1. **Swallowed exceptions** — 22 locations use `except Exception: pass`, 8 of which have zero logging or comments, silently hiding failures in the LLM pipeline, memory search, stats, and tool execution paths.
2. **Sync/async bridges** — 13 locations mix sync and async code via `run_until_complete`, `asyncio.run()`, `get_event_loop()`, and `run_coroutine_threadsafe()`. These are fragile patterns that throw `RuntimeError` when an event loop is already running, and are the #1 source of asyncio bugs in production.
3. **Low test coverage on critical paths** — `services/` (core LLM/TTS/ASR implementations) at 20% and `utils/` at 0% leaves the most business-critical and most changeprone code untested.

All three are internal implementation fixes — no API changes, no user-visible behavior changes, no breaking changes.

## Goals / Non-Goals

**Goals:**
- Eliminate all silent `except Exception: pass` blocks in production code paths
- Replace fragile sync/async bridge patterns with fully async alternatives
- Raise `services/` test coverage from 20% → 50% minimum
- Raise `utils/` test coverage from 0% → 40% minimum
- All changes must be behavior-preserving (no semantic changes to external interfaces)

**Non-Goals:**
- No API changes, no new features, no breaking changes
- Not fixing the broader `except Exception` pattern (278 instances with proper logging are acceptable)
- Not adding integration/E2E tests (scope-limited to unit test coverage)
- No refactoring beyond what's necessary for the fix
- No changes to frontend code

## Decisions

### D1: Exception handling strategy

| Pattern | Replacement | Rationale |
|---------|-------------|-----------|
| `except Exception: pass` (no log) | `except SpecificError: logger.exception("...")` | Never silently swallow — at minimum log the error |
| `except Exception: pass  # expected` | `contextlib.suppress(SpecificError)` | Intent clearer, still silent but explicit |
| `except Exception: logger.warning(...)` | Keep but narrow exception type if possible | Already logging is acceptable; narrow if feasible |
| Bare `except:` | `except Exception:` (or specific type) | Bare except catches `KeyboardInterrupt`/`SystemExit` |

### D2: Async bridge replacement strategy

| Location | Current Pattern | Replacement |
|----------|----------------|-------------|
| `stats_handler.py` sync→async bridge | `run_coroutine_threadsafe` / `run_until_complete` | Convert the caller graph node callback to async; use `asyncio.create_task` or `asyncio.to_thread` for the sync→async boundary |
| `bilibili_danmaku.py` event loop | `new_event_loop` + `run_until_complete` | Pass the running event loop reference; use `asyncio.run` only in `__main__` |
| `minecraft/tools.py` sync→async | `new_event_loop` + `run_until_complete` | Same pattern — accept loop parameter or use `asyncio.to_thread` |
| `socketio_server.py` shutdown | `run_until_complete(server.stop())` | Use `asyncio.get_running_loop().create_task()` in async context |
| `langchain_adapter.py` async bridge | `asyncio.run()` inside sync function | Caller should already be async — use `await` directly |

### D3: Coverage strategy

| Module | Current | Target | Approach |
|--------|---------|--------|----------|
| `services/intelligence/llm/` | ~20% | 50% | Add unit tests for provider factory, stream handler, tool handler; parameterized tests across providers |
| `services/speech/tts/` | ~20% | 50% | Add tests for interface conformance, factory routing, edge cases (empty input, errors) |
| `services/speech/asr/` | ~20% | 50% | Same pattern as TTS |
| `services/live/` | 0% | 30% | Integration-adjacent — mock socket layer |
| `services/live2d/` | 0% | 40% | Unit test action queue, viseme sync logic |
| `services/meme/` | ~20% | 40% | Analyzer logic, danmaku buffer |
| `utils/` | 0% | 40% | Unit test all 3 files (auto_config, env_helper, logger_manager) |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| [Async refactor] Changing event loop patterns may introduce subtle timing bugs | Each change must pass existing test suite; add async-specific tests for affected paths |
| [Exception fix] Over-narrowing exception types may miss edge cases | Prefer `logger.exception(...)` over narrowing for code paths where exception types are genuinely unpredictable |
| [Coverage] Tests for services/ require provider API access | Use existing mocks from `conftest.py` (mock_llm, mock_tts, mock_asr, mock_vad); verify mocks reflect real provider interfaces |
| [Coverage] Changing code to make it testable may introduce behavior changes | Minimally invasive changes — add type hints and extract interfaces only where necessary for testing |
| [Scope creep] 8 swallow locations + 13 async bridges + coverage across 6 modules is broad | Strict adherence to "fix only what's listed" — no refactoring adjacent code |
