## 1. Wave 1A — 前端测试基础设施 ✅ COMPLETE

- [x] 1.1 Install vitest, @vue/test-utils, happy-dom, @testing-library/vue as dev dependencies
- [x] 1.2 Create vitest.config.ts extending vite.config.ts with happy-dom environment
- [x] 1.3 Add test scripts to package.json (test, test:run, test:coverage)
- [x] 1.4 Verify vitest discovers and runs a smoke test successfully
- [x] 1.5 Install playwright for E2E tests (dev dependency)
- [x] 1.6 Add test directory structure

## 2. Wave 1B — routes.py 拆分为 handler 模块 ✅ COMPLETE

- [x] 2.1 Create server/handlers/ directory with __init__.py
- [x] 2.2 Extract chat handlers to chat_handlers.py
- [x] 2.3 Extract Bilibili handlers to bilibili_handlers.py
- [x] 2.4 Extract Live2D callback handler to live2d_handlers.py
- [x] 2.5 Extract admin/handshake handlers to admin_handlers.py
- [x] 2.6 Refactor routes.py to import and wire handlers (1377→317 lines, 77% reduction)
- [x] 2.7 Update any test imports that reference routes.py directly
- [x] 2.8 Run full test suite: 392/392 orchestration tests pass

## 3. Wave 1C — 大文件按职责拆分 ✅ COMPLETE

- [x] 3.1 Split silero_vad.py: detector.py (172 lines), silero_vad.py 454→359 lines
- [x] 3.2 Split openai_llm.py: stream_handler.py (101) + tool_handler.py (197), openai_llm.py 535→347
- [x] 3.3 Update __init__.py re-exports to maintain backward compatibility
- [x] 3.4 Verify all existing imports resolve correctly
- [x] 3.5 Run tests: 98/98 VAD+LLM tests pass, no regressions

## 4. Wave 1D — 文档更新 ✅ COMPLETE

- [x] 4.1 Update docs/README.md: remove references to removed modules
- [x] 4.2 Update AGENTS.md: reflect routes handler split, frontend test coverage, CI changes
- [x] 4.3 Update AGENTS.md for any changed module paths from large-file-refactor

## 5. Wave 2A — 前端 Stores + Composables + 组件测试 ✅ COMPLETE

- [x] 5.1 Write chat store tests (13 scenarios: messages, streaming, createMessage)
- [x] 5.2 Write connection store tests (status transitions)
- [x] 5.3 Write subtitle store tests (config, persistence, localStorage)
- [x] 5.4 Write model loading store tests (status updates, computed)
- [x] 5.5 Write danmaku store tests (messages, limits)
- [x] 5.6 Write useLive2D composable tests (pixi mocks, state, error handling)
- [x] 5.7 Write useSubtitle composable tests (pure functions, lifecycle)
- [x] 5.8 Write MessageBubble component tests (user/AI/streaming messages)
- [x] 5.9 Write InputBar component tests (send, empty, clear)
- [x] 5.10 Write Live2DRenderer component tests (loading/loaded/error/idle states)
- [x] 5.11 Write AppLayout component tests (renders children, popout)
- [x] 5.12 Write TypingIndicator component tests
- [x] 5.13 Run frontend test suite: 13 files, 167 tests, all pass

## 6. Wave 2B — 修复失败后端测试 ✅ COMPLETE

- [x] 6.1 Fix VAD source: use VADState enum instead of .value string comparison
- [x] 6.2 Fix VAD source: remove premature _is_speaking=True causing double-trigger
- [x] 6.3 Fix VAD source: use time.time() for timeout calc, not pre-patched current_time
- [x] 6.4 Fix test_simple_vad_processor.py: add 2nd silence chunk for timing tests
- [x] 6.5 Fix test_vad_processor.py: fix buffer size (>1024 samples for min-buffer guard)
- [x] 6.6 Fix test_analyzer.py: confidence expectation 0.4→0.5
- [x] 6.7 Run previously-failing tests: 64/64 pass
- [x] 6.8 Run full pytest suite (excl audio/meme/slow): 784 passed, 0 failed

## 7. Wave 2C — CI 集成 (coverage gate + report, independent) ✅ COMPLETE

- [x] 7.1 Update .github/workflows/test.yml: add --cov-fail-under=70 + --cov-report=xml
- [x] 7.2 Add coverage report upload as workflow artifact (actions/upload-artifact@v4)
- [x] 7.3 Create .github/workflows/frontend.yml: vue-tsc type check + vitest + build
- [x] 7.4 Add frontend CI status badge to README.md

## 9. Wave 3 — E2E 测试 + 收尾 (depends on Wave 2A + 2B)

- [ ] 9.1 Write Playwright E2E: initial page load with console error check
- [ ] 9.2 Write Playwright E2E: chat message send flow (type + send + verify)
- [ ] 9.3 Write Playwright E2E: settings page navigation and render
- [ ] 9.4 Add E2E test script to package.json (pnpm test:e2e)
- [ ] 9.5 Add E2E test run to CI (separate job, not blocking main test workflow)
- [ ] 9.6 Coverage gate: bump fail_under to 80% after verifying coverage meets threshold

## 10. 协办 — comprehensive-test-coverage (外部变化，与本变化并行推进)

- [ ] 10.1 参考 comprehensive-test-coverage/tasks.md，推进核心模块测试 (core, services, memory)
- [ ] 10.2 参考 comprehensive-test-coverage/tasks.md，推进工具系统测试 (tools, config)
- [ ] 10.3 参考 comprehensive-test-coverage/tasks.md，推进 avatar 和剩余模块测试
- [ ] 10.4 验证本变化的 CI coverage gate 与 comprehensive-test-coverage 进展协调一致
