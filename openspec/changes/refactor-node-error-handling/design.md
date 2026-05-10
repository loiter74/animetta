## Context

`llm_node.py` (352 lines) has two execution paths — `_llm_with_tools` and `_llm_without_tools` — that both independently perform RAG memory retrieval via `_retrieve_memory_context()`. This ~20-line block is duplicated identically. Additionally, when `interview-enhancements` adds timeout-based error resilience, each of the three graph nodes (LLM, TTS, ASR) would independently write error metadata to StatsStore with inconsistent formats. A shared utility avoids this inconsistency.

## Goals / Non-Goals

**Goals:**
- Eliminate RAG retrieval duplication in `llm_node.py` by hoisting it to the `llm_node()` entry point
- Create a shared `log_node_error()` function for structured StatsStore error reporting
- Preserve all existing behavior — no observable change from the outside
- Keep all 7 existing `test_llm_node.py` tests passing unmodified

**Non-Goals:**
- Not adding timeout or fallback logic (that's for `interview-enhancements`)
- Not changing the TTS/ASR node business logic (only adopting the new utility)
- Not modifying StatsStore schema (uses existing `attributes` and `status` columns)

## Decisions

### D1: RAG deduplication — Hoist to entry point, not extract to utility

- **Decision**: Perform RAG retrieval once in `llm_node()` before branching into `_llm_with_tools` / `_llm_without_tools`. Pass the retrieved `memory_context` as a parameter to both sub-functions.
- **Why**: The RAG retrieval result is needed by both paths identically. A separate utility would add indirection without value. Hoisting is the simplest refactoring — move 20 lines up, delete 20 lines from each branch, add 1 parameter to each sub-function.
- **Alternative considered**: Extract `_retrieve_memory_context()` as a standalone utility with caching. Overhead of caching logic is unnecessary — RAG is only called once per turn regardless.

### D2: Error logging — New file `node_error.py`, not inline in each node

- **Decision**: Create `src/anima/orchestration/graph/node_error.py` with a single `log_node_error()` async function. Nodes import and call it with structured arguments.
- **Why**: Centralizes error taxonomy. If error types or StatsStore schema change, only one file needs updating. Nodes remain thin.
- **Alternative considered**: Add error type to existing `stats_handler.py`. StatsHandler is a callback handler for LangChain/LangGraph internals — mixing application-level error reporting into it violates separation of concerns.

### D3: Error taxonomy — 4 enum values in Python, JSON in DB

- **Decision**: Define error types as module-level string constants: `"timeout"`, `"rate_limit"`, `"network_error"`, `"invalid_response"`. Store as JSON in the existing `spans.attributes` TEXT column.
- **Why**: No schema migration needed (attributes column already exists). Python constants are low-overhead — no need for a dedicated enum class for 4 values.
- **Alternative considered**: Add `error_type` column to spans table. Schema migration adds complexity and test surface with no benefit — the attributes column already serves as a flexible JSON extension point.

## Risks / Trade-offs

- [Risk] Moving RAG before branching may change timing slightly (RAG now happens even if LLM engine check fails) → **Mitigation**: The original code already validates engine presence after RAG in `_llm_without_tools`. Harden by moving engine validation BEFORE RAG in the entry point.
- [Risk] `node_error.py` creates a new import dependency chain → **Mitigation**: Uses only existing `get_stats_store()` singleton — no new dependencies. Import is internal to `orchestration/graph/` package.
