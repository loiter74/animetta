"""
Hybrid search: vector semantic + BM25 keyword weighted fusion.

Reference OpenClaw's hybrid.ts:39-111:
- Default weights: 70% vector + 30% keyword
- BM25 rank normalized to [0,1]
- Sort by fused score, deduplicate and return top-K

Formula:
final_score = vector_weight * vector_similarity + keyword_weight * keyword_score
keyword_score = 1 / (1 + rank)     # rank starts from 0, 0 is best
vector_similarity = 1 - cosine_distance
"""

from __future__ import annotations

from loguru import logger

from ..config import SearchConfig
from ..models.base import SearchResult
from ..storage.sqlite import SQLiteStore
from ..storage.chroma import ChromaStore


def hybrid_search(
    query: str,
    sqlite_store: SQLiteStore,
    chroma_store: ChromaStore,
    config: SearchConfig | None = None,
    max_results: int | None = None,
    min_score: float | None = None,
    query_embedding: list[float] | None = None,
) -> list[SearchResult]:
    """
    Hybrid search main flow.

    1. Get candidates from Chroma (vector) and SQLite FTS5 (keyword)
    2. Normalize each score to [0, 1]
    3. Weighted fusion
    4. Deduplicate, return top-K sorted by score descending

    Args:
        query: Search query text
        sqlite_store: SQLite store instance
        chroma_store: Chroma store instance
        config: Search configuration
        max_results: Maximum number of results to return
        min_score: Minimum score threshold
        query_embedding: Pre-computed query embedding (optional)

    Returns:
        List of SearchResult sorted by score descending
    """
    if config is None:
        config = SearchConfig()
    if max_results is None:
        max_results = config.default_max_results
    if min_score is None:
        min_score = config.default_min_score

    pool_size = max_results * config.candidate_multiplier

    # ── 1. Vector search ─────────────────────────────────
    vector_candidates: dict[int, float] = {}  # rowid -> similarity
    vector_metadata: dict[int, dict] = {}  # rowid -> metadata (includes oral_version)
    try:
        if query_embedding is not None:
            v_results = chroma_store.vector_search(
                query_embedding=query_embedding, n_results=pool_size
            )
        else:
            v_results = chroma_store.vector_search(
                query_text=query, n_results=pool_size
            )
        for chroma_id, distance, metadata in v_results:
            rowid = int(chroma_id)
            similarity = max(0.0, 1.0 - distance)  # Cosine distance -> similarity
            vector_candidates[rowid] = similarity
            vector_metadata[rowid] = metadata
    except Exception as e:
        logger.warning(f"[HybridSearch] Vector search failed, falling back to keyword-only: {e}")

    # ── 2. Keyword search (BM25) ─────────────────────────
    keyword_candidates: dict[int, float] = {}  # rowid -> normalized_score
    try:
        kw_results = sqlite_store.keyword_search(query, limit=pool_size)
        for rank_idx, (rowid, _bm25_rank) in enumerate(kw_results):
            # OpenClaw normalization: score = 1 / (1 + rank)
            # rank starts at 0; first gets 1.0, second gets 0.5, ...
            keyword_candidates[rowid] = 1.0 / (1.0 + rank_idx)
    except Exception as e:
        logger.warning(f"[HybridSearch] Keyword search failed, falling back to pure vector: {e}")

    # ── 3. Weighted fusion ───────────────────────────────
    all_rowids = set(vector_candidates.keys()) | set(keyword_candidates.keys())
    scored: list[tuple[int, float, float, float]] = []  # (rowid, final, vec, kw)

    for rowid in all_rowids:
        vec_score = vector_candidates.get(rowid, 0.0)
        kw_score = keyword_candidates.get(rowid, 0.0)
        final = config.vector_weight * vec_score + config.keyword_weight * kw_score
        scored.append((rowid, final, vec_score, kw_score))

    # Sort by fused score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 4. Build results ─────────────────────────────────
    results: list[SearchResult] = []
    for rowid, final_score, vec_score, kw_score in scored[:max_results]:
        if final_score < min_score:
            continue
        chunk = sqlite_store.get_chunk_by_rowid(rowid)
        if chunk is None:
            continue

        # Get colloquial version from Chroma metadata
        metadata = vector_metadata.get(rowid, {})
        oral_version = metadata.get("oral_version", "") or None

        # Prefer colloquial version, fall back to original text
        display_text = oral_version if oral_version else chunk.text
        results.append(
            SearchResult(
                text=display_text,
                path=chunk.path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                score=final_score,
                source=chunk.source,
                vector_score=vec_score,
                keyword_score=kw_score,
                oral_version=oral_version,
            )
        )

    return results
