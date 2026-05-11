## 1. Core Implementation

- [x] 1.1 Add decay fields to MemoryEntry model (`decay_created_at`, `retrieval_count`, `last_accessed_at`)
- [x] 1.2 Implement decay function in `MemoryScorer`: `score *= f(time, emotion, retrieval_count)`
- [x] 1.3 Add archive threshold and auto-archive logic in `MemoryManager`
- [x] 1.4 Exclude archived memories from default search results
