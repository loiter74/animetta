## 1. Create node_error.py utility

- [x] 1.1 Create `src/anima/orchestration/graph/node_error.py` with `log_node_error()` async function, `VALID_ERROR_TYPES` frozenset, and `LOGGER = logger.bind(name="NodeError")`
- [x] 1.2 Implement error type validation: map unknown types to `"unknown"` with debug warning
- [x] 1.3 Implement StatsStore span creation: create span with `status="error"` and `attributes` JSON containing `error_type`, `provider`, `duration_ms`
- [x] 1.4 Handle missing trace_id: skip span creation when `trace_id is None`, log warning

## 2. Write tests for node_error utility

- [x] 2.1 Create `tests/orchestration/graph/test_node_error.py` with test fixture for StatsStore
- [x] 2.2 Test: `log_node_error()` creates span with correct error_type and attributes
- [x] 2.3 Test: invalid error_type defaults to `"unknown"` 
- [x] 2.4 Test: `trace_id=None` skips span creation and logs warning
- [x] 2.5 Run tests: `PYTHONPATH=src python -m pytest tests/orchestration/graph/test_node_error.py -v`

## 3. Deduplicate RAG in llm_node.py

- [x] 3.1 Move engine validation (lines 170-178) BEFORE RAG retrieval in `llm_node()` entry point
- [x] 3.2 Move RAG retrieval (from lines 294-303 of `_llm_without_tools`) to `llm_node()` entry point after engine validation
- [x] 3.3 Pass `memory_context` result to both `_llm_with_tools()` and `_llm_without_tools()` as new parameter
- [x] 3.4 Remove duplicate RAG retrieval from `_llm_with_tools()` (lines 208-219) — use passed-in `memory_context`
- [x] 3.5 Remove duplicate RAG retrieval from `_llm_without_tools()` — use passed-in `memory_context`
- [x] 3.6 Verify: run existing tests `PYTHONPATH=src python -m pytest tests/orchestration/graph/test_llm_node.py -v` — all 7 must pass

## 4. Adopt log_node_error() in graph nodes

- [x] 4.1 Import `log_node_error` in `llm_node.py` — add to existing error handling paths (engine missing, service_context missing)
- [x] 4.2 Import `log_node_error` in `tts_node.py` — call when `tts_engine.synthesize()` raises exception
- [x] 4.3 Import `log_node_error` in `asr_node.py` — call when `asr_engine.transcribe()` raises exception
- [x] 4.4 Verify: run full graph test suite — `PYTHONPATH=src python -m pytest tests/orchestration/graph/ -v`
- [ ] 4.5 Commit: `git add -A && git commit -m "refactor: deduplicate RAG in llm_node and add shared node_error logger"`
