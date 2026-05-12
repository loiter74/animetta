
# RAG Evaluation Report — bm25_only

**Generated:** 2026-05-12T17:45:43.645136+00:00
**Git commit:** `9ab37cf`

---

## Experiment Configuration

| Parameter | Value |
|-----------|-------|
| Vector weight | 0.0 |
| Keyword weight | 1.0 |
| Embedding model | `BAAI/bge-small-zh-v1.5` |
| Target tokens | 400 |
| Overlap tokens | 80 |
| Fuzzy layer | False |
| Max results (k) | 5 |

**Description:** Pure SQLite FTS5 BM25


---

## Overall Metrics (k=5)

| Metric | Value |
|--------|-------|
| Recall@k | 0.2615 |
| Precision@k | 0.0621 |
| MRR | 0.1190 |
| NDCG@k | 0.1529 |
| Chunk Diversity | 0.4828 |
| Total Queries | 58 |

---

## Latency Distribution

| Percentile | Latency (ms) |
|------------|-------------|
| P50 (median) | 10.7 |
| P75 | 11.4 |
| P90 | 11.7 |
| P95 | 11.8 |
| P99 | 12.4 |
| Mean | 10.8 |
| Min | 9.3 |
| Max | 12.8 |

---

## Per-Category Breakdown

| Category | Recall@k | Precision@k | MRR | NDCG@k | Avg Latency (ms) | Count |
|----------|----------|------------|-----|--------|-----------------|-------|

| contextual | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 11.2 | 10 |

| factual | 0.6923 | 0.1385 | 0.3333 | 0.4219 | 10.5 | 13 |

| multi_hop | 0.2167 | 0.1000 | 0.0900 | 0.1122 | 11.1 | 10 |

| persona | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 10.8 | 10 |

| robustness | 0.8000 | 0.1600 | 0.3333 | 0.4524 | 10.3 | 5 |

| temporal | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 10.6 | 10 |


---

## Per-Difficulty Breakdown

| Difficulty | Queries | Avg Recall@k |
|------------|---------|-------------|

| easy | 14 | 0.6429 |

| hard | 16 | 0.1354 |

| medium | 28 | 0.1429 |


---

## Notes

- All metrics computed at **k=5**
- Chunk identifiers are `(path, start_line, end_line)` tuples
- Latency measured from query submission to results returned
- FuzzyLayer enabled: False