
# RAG Evaluation Report — c1024

**Generated:** 2026-05-12T17:51:32.073749+00:00
**Git commit:** `9ab37cf`

---

## Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Vector weight | 0.7 |
| Keyword weight | 0.3 |
| Embedding model | `BAAI/bge-small-zh-v1.5` |
| Target tokens | 1024 |
| Overlap tokens | 200 |
| Fuzzy layer | False |
| Max results (k) | 5 |

**Description:** X-Large chunks (1024 tokens)


---

## Overall Metrics (k=5)

| Metric | Value |
|--------|-------|
| Recall@k | 0.3563 |
| Precision@k | 0.0828 |
| MRR | 0.2497 |
| NDCG@k | 0.2696 |
| Chunk Diversity | 0.9172 |
| Total Queries | 58 |

---

## Latency Distribution

| Percentile | Latency (ms) |
|------------|-------------|
| P50 (median) | 10.9 |
| P75 | 11.4 |
| P90 | 11.9 |
| P95 | 12.0 |
| P99 | 12.7 |
| Mean | 11.0 |
| Min | 9.5 |
| Max | 12.9 |

---

## Per-Category Breakdown

| Category | Recall@k | Precision@k | MRR | NDCG@k | Avg Latency (ms) | Count |
|----------|----------|------------|-----|--------|-----------------|-------|

| contextual | 0.2000 | 0.0400 | 0.1200 | 0.1387 | 11.2 | 10 |

| factual | 0.7692 | 0.1538 | 0.5603 | 0.6114 | 10.5 | 13 |

| multi_hop | 0.2667 | 0.1200 | 0.2000 | 0.1779 | 11.2 | 10 |

| persona | 0.1000 | 0.0200 | 0.0500 | 0.0631 | 11.3 | 10 |

| robustness | 0.8000 | 0.1600 | 0.6000 | 0.6524 | 10.9 | 5 |

| temporal | 0.1000 | 0.0200 | 0.0500 | 0.0631 | 10.9 | 10 |


---

## Per-Difficulty Breakdown

| Difficulty | Queries | Avg Recall@k |
|------------|---------|-------------|

| easy | 14 | 0.7857 |

| hard | 16 | 0.1667 |

| medium | 28 | 0.2500 |


---

## Notes

- All metrics computed at **k=5**
- Chunk identifiers are `(path, start_line, end_line)` tuples
- Latency measured from query submission to results returned
- FuzzyLayer enabled: False