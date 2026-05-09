## Why

The memory system's background processing tasks (consolidation, pattern extraction, meme generation) have several incremental-processing bugs: `consolidate_conversations` silently exits without doing work (0.0s), `_processed_sessions` is lost on restart causing full re-processing, and pattern extraction doesn't track what's already been processed, leading to duplicate work.

## What Changes

- Fix `consolidate_conversations` to actually read and process conversation turns (currently silently returns early due to `hasattr` check on wrong attribute)
- Persist `_processed_sessions` so restart doesn't cause re-processing of all historical data
- Add processed-log tracking for pattern extraction to prevent duplicate extraction from the same summaries
- Fix `prune_logs` to use actual date-based cleanup instead of arbitrary session count limit
- Fix `_get_recent_logs` to respect retention windows correctly

## Capabilities

### New Capabilities
*(None — this is a bugfix within existing capabilities)*

### Modified Capabilities
*(None — no spec-level requirement changes, only implementation-level bugfixes)*

## Impact

- **`src/anima/memory/learner/engine.py`**: `consolidate_conversations` logic, processed-session tracking, prune_logs, `_get_recent_logs`
- **`src/anima/memory/learner/summarizer.py`** (if applicable): data access pattern
- **`src/anima/memory/system.py`**: If `ShortTermMemory` interface needs adjustment
