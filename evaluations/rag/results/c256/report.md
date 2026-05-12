
# RAG Evaluation Report — c256

**Generated:** 2026-05-12T17:50:47.129349+00:00
**Git commit:** `9ab37cf`

---

## Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Vector weight | 0.7 |
| Keyword weight | 0.3 |
| Embedding model | `BAAI/bge-small-zh-v1.5` |
| Target tokens | 256 |
| Overlap tokens | 50 |
| Fuzzy layer | False |
| Max results (k) | 5 |

**Description:** Small chunks (256 tokens)


---

## Overall Metrics (k=5)

| Metric | Value |
|--------|-------|
| Recall@k | 0.2126 |
| Precision@k | 0.0483 |
| MRR | 0.1658 |
| NDCG@k | 0.1723 |
| Chunk Diversity | 0.7103 |
| Total Queries | 58 |

---

## Latency Distribution

| Percentile | Latency (ms) |
|------------|-------------|
| P50 (median) | 10.8 |
| P75 | 11.3 |
| P90 | 11.7 |
| P95 | 12.5 |
| P99 | 13.2 |
| Mean | 10.8 |
| Min | 9.0 |
| Max | 13.8 |

---

## Per-Category Breakdown

| Category | Recall@k | Precision@k | MRR | NDCG@k | Avg Latency (ms) | Count |
|----------|----------|------------|-----|--------|-----------------|-------|

| contextual | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 11.2 | 10 |

| factual | 0.5385 | 0.1077 | 0.4769 | 0.4913 | 10.4 | 13 |

| multi_hop | 0.1333 | 0.0600 | 0.1250 | 0.0976 | 10.9 | 10 |

| persona | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 10.7 | 10 |

| robustness | 0.8000 | 0.1600 | 0.4333 | 0.5262 | 10.3 | 5 |

| temporal | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 11.2 | 10 |


---

## Per-Difficulty Breakdown

| Difficulty | Queries | Avg Recall@k |
|------------|---------|-------------|

| easy | 14 | 0.5000 |

| hard | 16 | 0.0833 |

| medium | 28 | 0.1429 |


---

## Notes

- All metrics computed at **k=5**
- Chunk identifiers are `(path, start_line, end_line)` tuples
- Latency measured from query submission to results returned
- FuzzyLayer enabled: False