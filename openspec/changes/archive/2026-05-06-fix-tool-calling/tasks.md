## 1. Fix ChatModel Creation

- [x] 1.1 Add proxy unwrapping logic at the start of `create_chat_model_from_service()` in `src/anima/services/intelligence/llm/langchain_adapter.py`
- [x] 1.2 Verify: syntax check passes, logic handles TracingProxy via `hasattr('_target')` duck-typing

## 2. Verification

- [x] 2.1 Run `python -m pytest tests/ -v` — **159/159 passed** (3.84s)
- [x] 2.2 Start server and confirm no `ChatModel creation failed` error — connection test passed
- [ ] 2.3 Optionally: trigger a tool call (e.g., "搜索今天的新闻") and verify tool execution works (manual — requires running server)
