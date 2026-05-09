## 1. Fix `consolidate_conversations` to read from ShortTermMemory

- [x] 1.1 Fix attribute name: `_sessions` → `_cache` in the `hasattr` check
- [x] 1.2 Fix iteration: use `short_term._cache.items()` (returns `Dict[str, deque]`), convert deque to list for processing
- [x] 1.3 Store returned LearningLogs: add SQLite table `learning_logs` and persist logs after summarization

## 2. Implement LearningLog storage and retrieval

- [x] 2.1 Add `init_storage()` to create `learning_logs` table (id, session_id, summary_type, content, source_ids, created_at)
- [x] 2.2 Add `_store_logs(logs: List[LearningLog])` to batch-insert learning logs
- [x] 2.3 Fix `_get_recent_logs(log_type)` to query from SQLite by type and time window
- [x] 2.4 Fix `_content_to_turns(log)` to parse stored JSON source_turn_ids and reconstruct MemoryTurns

## 3. Persist `_processed_sessions` across restarts

- [x] 3.1 Add `processed_sessions` table (session_id TEXT PRIMARY KEY, processed_at TIMESTAMP)
- [x] 3.2 Load sessions from DB on `__init__`
- [x] 3.3 Upsert session_id with timestamp on each consolidation run
- [x] 3.4 Add `_processed_log_ids` set (track which LearningLogs have been fed to pattern extraction) and persist alongside

## 4. Fix `prune_logs` with real date-based cleanup

- [x] 4.1 Query `processed_sessions` for entries older than `_log_retention_days`, delete them
- [x] 4.2 Query `learning_logs` for entries older than retention, delete them
- [x] 4.3 Remove the broken arbitrary-10-sessions logic

## 5. Verify

- [x] 5.1 Backend Python parses clean
- [x] 5.2 Existing tests pass
