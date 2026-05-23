# EVALUATIONS — STANDALONE RAG EVALUATION FRAMEWORK

**Generated:** 2026-05-23
**Commit:** 8930c5f

> Parent: [../AGENTS.md](../AGENTS.md) — root project conventions. ⚠️ This is a SEPARATE Python tree, not part of src/animetta/.

## OVERVIEW
Standalone RAG (Retrieval-Augmented Generation) evaluation framework for benchmarking the memory system's retrieval quality. Lives outside both src/animetta/ and tests/ — runs as its own Python package.

## STRUCTURE
```
evaluations/rag/
├── runner.py                # Evaluation runner — orchestrates test runs
├── metrics.py               # RAG metrics: recall, precision, MRR, NDCG
├── dataset_builder.py       # Dataset construction from memory
├── dataset.jsonl            # Test queries (6 categories, 50+ queries)
├── config.py                # Evaluation configuration
├── conftest.py              # Eval-specific fixtures (sample data)
└── test_rag_quality.py      # Quality tests marked as 'slow' in CI
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Run evaluation | `runner.py` | `python evaluations/rag/runner.py` |
| Add test queries | `dataset.jsonl` | JSONL format, 6 categories |
| Change metrics | `metrics.py` | Recall, precision, MRR, NDCG |
| CI integration | `.github/workflows/test.yml` | RAG eval job runs after test matrix |

## KEY PATTERNS
- **Separate PYTHONPATH**: `PYTHONPATH=evaluations/rag` — not part of src/animetta
- **slow marker**: RAG quality tests use pytest `slow` marker — skipped in default test runs
- **dataset.jsonl**: JSONL with expected retrieval results per query

## NOTES
- Not imported by any code in src/animetta/ — fully standalone evaluation tool
- CI runs RAG eval as a separate job with `-m "slow" --timeout=300`
- Dataset categories: factual, conceptual, temporal, personal, ambiguous, multi-hop
