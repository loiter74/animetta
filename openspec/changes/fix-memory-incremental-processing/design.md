## Context

Four bugs in the PeriodLearner background processing tasks:

1. **Wrong attribute name in `consolidate_conversations`** — Checks `hasattr(short_term, '_sessions')` but `ShortTermMemory` stores data in `self._cache` (a `Dict[str, deque]`). The check always returns False, so the function silently exits without processing any data. Explains the 0.0s completion time.

2. **`_processed_sessions` is in-memory only** — A Python `set()` on the `PeriodicLearner` instance. Lost on server restart, causing every session to be re-consolidated from scratch.

3. **No processed-log tracking for pattern extraction** — `extract_patterns` calls `_get_recent_logs("conversation")` which returns a time-windowed list. But there's no tracking of which logs were already extracted, so the same summaries can be processed repeatedly.

4. **`prune_logs` has broken date logic** — Instead of actually checking log dates against the retention cutoff, it arbitrarily discards 10 session IDs from `_processed_sessions` regardless of their actual age.

## Goals / Non-Goals

**Goals:**
- Fix `consolidate_conversations` so it actually processes new turns from short-term memory
- Persist `_processed_sessions` across restarts (SQLite)
- Add processed-LearningLog tracking for pattern extraction
- Fix `prune_logs` to do real date-based cleanup
- Keep all changes minimal — bugfix only

**Non-Goals:**
- No redesign of the memory pipeline architecture
- No new capabilities or API changes
- No changes to `FuzzyConsolidator` or `MemePool`

## Decisions

1. **Fix `_sessions` → `_cache`** — Straightforward attribute name fix. Additionally use `get_session_ids()` (existing public API) instead of directly accessing `_cache` to stay within the public interface.

2. **Persist `_processed_sessions` via SQLite** — The `PeriodicLearner` already has access to the learner storage (LearningLog SQLite). Add a simple `processed_sessions` table with a `(session_id, processed_at)` schema. On init, load from DB. On each processing, upsert. Avoids adding new dependencies.

3. **Track processed LearningLog IDs** — Add a `processed_log_id` set (in-memory for now, persisted alongside `_processed_sessions`). Before extracting patterns, check if a log's ID has already been processed.

4. **Fix `prune_logs`** — Query the `processed_sessions` table for entries older than retention_days, delete them. Same for processed_log_ids. Use actual timestamp comparison instead of arbitrary count-based cleanup.

## Risks / Trade-offs

- **[Low] Persistence adds DB writes** — Each consolidation or pattern extraction cycle adds a small write. Acceptable for a background task running every few hours.
- **[Low] LearningLog ID dedup** — IDs are UUIDs, so collision is not a concern.
