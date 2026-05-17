## 1. Fix Swallowed Exceptions (except Exception: pass)

- [x] 1.1 Fix `memory/search/hybrid.py:78` — add logging + graceful degradation comment
- [x] 1.2 Fix `memory/search/hybrid.py:89` — add logging + graceful degradation comment
- [x] 1.3 Fix `memory/wiki/models.py:103` — replace bare pass with logged warning
- [x] 1.4 Fix `memory/wiki/organizer.py:198` — replace bare pass with logged warning
- [x] 1.5 Fix `orchestration/graph/llm_node.py:217` — replace bare pass with `logger.exception()` and re-raise
- [x] 1.6 Fix `orchestration/graph/stats_handler.py:196` — replace bare pass with `logger.warning`
- [x] 1.7 Fix `orchestration/graph/stats_handler.py:221` — replace bare pass with `logger.warning`
- [x] 1.8 Fix `orchestration/graph/stats_store.py:72` — replace bare pass with `logger.warning`
- [x] 1.9 Fix `orchestration/graph/tool_node.py:117` — add `logger.exception("Tool execution failed")`
- [x] 1.10 Fix `orchestration/graph/tool_node.py:132` — add `logger.exception("Tool iteration failed")`
- [x] 1.11 Fix `core/model_loading_manager.py:287` — add `logger.warning` with context
- [x] 1.12 Fix `services/intelligence/llm/glm_llm.py:188` — add `logger.warning` with context
- [x] 1.13 Fix `services/intelligence/llm/local_lora_llm.py:87` — replace bare `except:` with `except Exception` + logging
- [x] 1.14 Fix `tools/base.py:100` — replace bare `except:` with `except Exception` + logging
- [x] 1.15 Fix `utils/auto_config.py:52,74` — replace bare `except:` with `except Exception` + logging
- [x] 1.16 Fix remaining `except Exception: pass` in `orchestration/server/handlers/` (admin_handlers.py:139,161,242,506, chat_handlers.py:53,74)
- [x] 1.17 Fix `services/speech/asr/faster_whisper_asr.py:136` — add `logger.warning` for file read failure (already handled — no bare except found)
- [x] 1.18 Fix `memory/search/hybrid.py:66` — add `logger.warning` for embedding failure (covered by 1.1 fix)
- [x] 1.19 Verify: all `except Exception: pass` eliminated from production code; run full test suite

## 2. Fix Sync/Async Bridge Patterns

- [x] 2.1 Refactor `orchestration/graph/stats_handler.py` — convert `_dispatch_stats_record` from sync bridge to fully async; use `asyncio.create_task` in the calling context
- [x] 2.2 Refactor `services/live/bilibili_danmaku.py` — pass running event loop to `BilibiliDanmakuClient`; remove `new_event_loop` + `run_until_complete` pattern
- [x] 2.3 Refactor `tools/minecraft/tools.py` — replace `new_event_loop` + `run_until_complete` with `asyncio.to_thread` or accept loop parameter
- [x] 2.4 Fix `core/socketio_server.py:113` — replace `loop.run_until_complete(server.stop())` with proper async shutdown in async context
- [x] 2.5 Fix `services/intelligence/llm/langchain_adapter.py:66` — replace `asyncio.run()` with `await` (caller must be async)
- [x] 2.6 Fix `services/intelligence/llm/ollama_llm.py:134,178` — replace `get_event_loop()` with explicit loop parameter or `asyncio.to_thread`
- [x] 2.7 Fix `services/intelligence/vad/silero_vad.py:81` — replace `get_event_loop()` with proper async pattern
- [x] 2.8 Verify: no `run_until_complete`, `asyncio.run()`, or `get_event_loop()` remains in production code; run full test suite

## 3. Improve Test Coverage — services/

- [x] 3.1 Add `tests/services/intelligence/llm/test_providers.py` — parameterized contract tests verifying all LLM providers implement interface correctly
- [x] 3.2 Add `tests/services/intelligence/llm/test_stream_handler.py` — test streaming buffer, chunk accumulation, completion detection
- [x] 3.3 Add `tests/services/intelligence/llm/test_tool_handler.py` — test tool call parsing, tool result formatting
- [x] 3.4 Add `tests/services/speech/tts/test_factory.py` — test provider factory routing, fallback logic, config validation
- [x] 3.5 Add `tests/services/speech/tts/test_interface_conformance.py` — test that all TTS providers satisfy interface contract
- [x] 3.6 Add `tests/services/speech/asr/test_factory.py` — test ASR provider factory routing
- [x] 3.7 Add `tests/services/speech/asr/test_interface_conformance.py` — test ASR provider contract
- [x] 3.8 Add `tests/services/live/test_bilibili_danmaku.py` — test connection lifecycle, danmaku parsing, reconnection logic (with mocked socket)
- [x] 3.9 Add `tests/services/live2d/test_action_queue.py` — test action scheduling, priority, cancellation
- [x] 3.10 Add `tests/services/live2d/test_viseme_sync.py` — test audio→viseme mapping with known inputs
- [x] 3.11 Add `tests/services/meme/test_analyzer.py` — test cognitive analysis logic with fixture data
- [x] 3.12 Add `tests/services/meme/test_danmaku_buffer.py` — test buffer insert, flush, dedup
- [x] 3.13 Run coverage report: verify `services/` reaches 50%+

## 4. Improve Test Coverage — utils/

- [x] 4.1 Add `tests/utils/test_auto_config.py` — test config auto-detection, path resolution, env expansion
- [x] 4.2 Add `tests/utils/test_env_helper.py` — test env variable reading, defaults, type coercion
- [x] 4.3 Add `tests/utils/test_logger_manager.py` — test logger setup, level configuration, rotation
- [x] 4.4 Run coverage report: verify `utils/` reaches 40%+

## 5. Verification

- [x] 5.1 Run `mypy src/ --ignore-missing-imports` — no new type errors
- [x] 5.2 Run `ruff check src/ tests/` — no new lint violations
- [x] 5.3 Run `PYTHONPATH=src python -m pytest tests/ -v --tb=short` — all tests pass
- [x] 5.4 Run `PYTHONPATH=src python -m pytest tests/ --cov=src/anima --cov-report=term-missing` — verify coverage targets met
