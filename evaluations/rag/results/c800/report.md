
# RAG Evaluation Report — c800

**Generated:** 2026-05-12T17:51:18.320985+00:00
**Git commit:** `9ab37cf`

---

## Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Vector weight | 0.7 |
| Keyword weight | 0.3 |
| Embedding model | `BAAI/bge-small-zh-v1.5` |
| Target tokens | 800 |
| Overlap tokens | 160 |
| Fuzzy layer | False |
| Max results (k) | 5 |

**Description:** Large chunks (800 tokens)


---

## Overall Metrics (k=5)

| Metric | Value |
|--------|-------|
| Recall@k | 0.3736 |
| Precision@k | 0.0862 |
| MRR | 0.2497 |
| NDCG@k | 0.2736 |
| Chunk Diversity | 0.8483 |
| Total Queries | 58 |

---

## Latency Distribution

| Percentile | Latency (ms) |
|------------|-------------|
| P50 (median) | 10.6 |
| P75 | 11.0 |
| P90 | 11.8 |
| P95 | 12.1 |
| P99 | 12.6 |
| Mean | 10.5 |
| Min | 8.4 |
| Max | 13.2 |

---

## Per-Category Breakdown

| Category | Recall@k | Precision@k | MRR | NDCG@k | Avg Latency (ms) | Count |
|----------|----------|------------|-----|--------|-----------------|-------|

| contextual | 0.2000 | 0.0400 | 0.1200 | 0.1387 | 10.9 | 10 |

| factual | 0.8462 | 0.1692 | 0.5603 | 0.6291 | 10.3 | 13 |

| multi_hop | 0.2667 | 0.1200 | 0.2000 | 0.1779 | 11.1 | 10 |

| persona | 0.1000 | 0.0200 | 0.0500 | 0.0631 | 9.8 | 10 |

| robustness | 0.8000 | 0.1600 | 0.6000 | 0.6524 | 10.3 | 5 |

| temporal | 0.1000 | 0.0200 | 0.0500 | 0.0631 | 10.6 | 10 |


---

## Per-Difficulty Breakdown

| Difficulty | Queries | Avg Recall@k |
|------------|---------|-------------|

| easy | 14 | 0.7857 |

| hard | 16 | 0.1667 |

| medium | 28 | 0.2857 |


---

## Notes

- All metrics computed at **k=5**
- Chunk identifiers are `(path, start_line, end_line)` tuples
- Latency measured from query submission to results returned
- FuzzyLayer enabled: False