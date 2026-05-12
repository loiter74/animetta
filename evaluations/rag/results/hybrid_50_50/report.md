
# RAG Evaluation Report — hybrid_50_50

**Generated:** 2026-05-12T17:46:21.587266+00:00
**Git commit:** `9ab37cf`

---

## Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Vector weight | 0.5 |
| Keyword weight | 0.5 |
| Embedding model | `BAAI/bge-small-zh-v1.5` |
| Target tokens | 400 |
| Overlap tokens | 80 |
| Fuzzy layer | False |
| Max results (k) | 5 |

**Description:** Equal weight baseline


---

## Overall Metrics (k=5)

| Metric | Value |
|--------|-------|
| Recall@k | 0.2989 |
| Precision@k | 0.0655 |
| MRR | 0.2009 |
| NDCG@k | 0.2184 |
| Chunk Diversity | 0.7276 |
| Total Queries | 58 |

---

## Latency Distribution

| Percentile | Latency (ms) |
|------------|-------------|
| P50 (median) | 10.7 |
| P75 | 11.4 |
| P90 | 14.7 |
| P95 | 34.0 |
| P99 | 48.2 |
| Mean | 13.1 |
| Min | 9.4 |
| Max | 49.3 |

---

## Per-Category Breakdown

| Category | Recall@k | Precision@k | MRR | NDCG@k | Avg Latency (ms) | Count |
|----------|----------|------------|-----|--------|-----------------|-------|

| contextual | 0.2000 | 0.0400 | 0.0450 | 0.0818 | 13.2 | 10 |

| factual | 0.5385 | 0.1077 | 0.4769 | 0.4913 | 19.6 | 13 |

| multi_hop | 0.1333 | 0.0600 | 0.1500 | 0.1070 | 10.7 | 10 |

| persona | 0.2000 | 0.0400 | 0.1333 | 0.1500 | 10.3 | 10 |

| robustness | 0.8000 | 0.1600 | 0.3667 | 0.4786 | 10.7 | 5 |

| temporal | 0.1000 | 0.0200 | 0.0333 | 0.0500 | 10.8 | 10 |


---

## Per-Difficulty Breakdown

| Difficulty | Queries | Avg Recall@k |
|------------|---------|-------------|

| easy | 14 | 0.5714 |

| hard | 16 | 0.0833 |

| medium | 28 | 0.2857 |


---

## Notes

- All metrics computed at **k=5**
- Chunk identifiers are `(path, start_line, end_line)` tuples
- Latency measured from query submission to results returned
- FuzzyLayer enabled: False