## Why

Before adding error resilience (timeout + fallback) to LLM/TTS/ASR nodes for `interview-enhancements`, two structural issues must be fixed to prevent code rot: RAG retrieval is duplicated across `_llm_with_tools` and `_llm_without_tools` in `llm_node.py`, and the three graph nodes (LLM, TTS, ASR) lack a consistent error-reporting pattern — each would invent its own error logging if we add fallback now.

## What Changes

- **Deduplicate RAG retrieval** in `llm_node.py`: extract shared RAG logic from both tool-calling and streaming paths into a single call at the `llm_node()` entry point. Reduces `llm_node.py` by ~20 lines and eliminates the main source of code duplication.
- **Add `log_node_error()` utility**: create a shared function that all three graph nodes (LLM/TTS/ASR) use to log errors to StatsStore with structured metadata (error_type, provider name, duration). Ensures consistent error taxonomy when fallback logic is later added.
- **No breaking changes** — all existing behavior preserved. Existing 7 `test_llm_node.py` tests continue to pass unmodified.

## Capabilities

### New Capabilities
- `node-error-logging`: Shared utility for graph nodes to report structured errors to StatsStore. Covers error_type classification (timeout, rate_limit, network_error, invalid_response), provider identification, and consistent log format across LLM/TTS/ASR nodes.

### Modified Capabilities
<!-- None — internal refactoring only, no spec-level behavior changes -->

## Impact

- Modified: `src/anima/orchestration/graph/llm_node.py` — deduplicate RAG, ~310 lines (from 352)
- Modified: `src/anima/orchestration/graph/tts_node.py` — adopt `log_node_error()`, +3 lines
- Modified: `src/anima/orchestration/graph/asr_node.py` — adopt `log_node_error()`, +3 lines  
- New: `src/anima/orchestration/graph/node_error.py` — shared utility, ~25 lines
- No dependency changes — uses existing StatsStore via `get_stats_store()`
