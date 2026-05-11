## 1. Core Implementation

- [x] 1.1 Add `emotion_value` field to MemoryEntry model (nullable, float 0-1)
- [x] 1.2 Modify `MemoryScorer` in `scorer.py` to compute emotion weight
- [x] 1.3 Integrate emotion weight into `hybrid_search()` score fusion
- [x] 1.4 Implement emotion-contingent decay in scorer
