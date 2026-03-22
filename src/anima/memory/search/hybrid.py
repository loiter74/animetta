"""
混合搜索: 向量语义 + BM25 关键词加权融合.

参考 OpenClaw 的 hybrid.ts:39-111:
- 默认权重: 70% 向量 + 30% 关键词
- BM25 rank 归一化到 [0,1]
- 按融合分数排序, 去重后返回 top-K

公式:
    final_score = vector_weight * vector_similarity + keyword_weight * keyword_score
    keyword_score = 1 / (1 + rank)     # rank 从 0 开始, 0 最好
    vector_similarity = 1 - cosine_distance
"""

from __future__ import annotations

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
    执行混合检索.

    1. 分别从 Chroma (向量) 和 SQLite FTS5 (关键词) 获取候选
    2. 归一化各自分数到 [0, 1]
    3. 加权融合
    4. 去重, 按分数降序返回 top-K

    Args:
        query: 搜索查询文本
        sqlite_store: SQLite 存储实例
        chroma_store: Chroma 存储实例
        config: 搜索配置
        max_results: 返回结果数上限
        min_score: 最低分数阈值
        query_embedding: 预计算的查询向量 (可选)

    Returns:
        按分数降序排列的 SearchResult 列表
    """
    if config is None:
        config = SearchConfig()
    if max_results is None:
        max_results = config.default_max_results
    if min_score is None:
        min_score = config.default_min_score

    pool_size = max_results * config.candidate_multiplier

    # ── 1. 向量检索 ──────────────────────────────────────
    vector_candidates: dict[int, float] = {}  # rowid -> similarity
    try:
        if query_embedding is not None:
            v_results = chroma_store.vector_search(
                query_embedding=query_embedding, n_results=pool_size
            )
        else:
            v_results = chroma_store.vector_search(
                query_text=query, n_results=pool_size
            )
        for chroma_id, distance in v_results:
            rowid = int(chroma_id)
            similarity = max(0.0, 1.0 - distance)  # 余弦距离 -> 相似度
            vector_candidates[rowid] = similarity
    except Exception:
        pass  # 向量搜索失败时降级为纯关键词搜索

    # ── 2. 关键词检索 (BM25) ─────────────────────────────
    keyword_candidates: dict[int, float] = {}  # rowid -> normalized_score
    try:
        kw_results = sqlite_store.keyword_search(query, limit=pool_size)
        for rank_idx, (rowid, _bm25_rank) in enumerate(kw_results):
            # OpenClaw 的归一化: score = 1 / (1 + rank)
            # rank 从 0 开始, 第一名得 1.0, 第二名得 0.5, ...
            keyword_candidates[rowid] = 1.0 / (1.0 + rank_idx)
    except Exception:
        pass  # FTS 搜索失败时降级为纯向量搜索

    # ── 3. 加权融合 ──────────────────────────────────────
    all_rowids = set(vector_candidates.keys()) | set(keyword_candidates.keys())
    scored: list[tuple[int, float, float, float]] = []  # (rowid, final, vec, kw)

    for rowid in all_rowids:
        vec_score = vector_candidates.get(rowid, 0.0)
        kw_score = keyword_candidates.get(rowid, 0.0)
        final = config.vector_weight * vec_score + config.keyword_weight * kw_score
        scored.append((rowid, final, vec_score, kw_score))

    # 按融合分数降序
    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 4. 构建结果 ──────────────────────────────────────
    results: list[SearchResult] = []
    for rowid, final_score, vec_score, kw_score in scored[:max_results]:
        if final_score < min_score:
            continue
        chunk = sqlite_store.get_chunk_by_rowid(rowid)
        if chunk is None:
            continue
        results.append(
            SearchResult(
                text=chunk.text,
                path=chunk.path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                score=final_score,
                source=chunk.source,
                vector_score=vec_score,
                keyword_score=kw_score,
            )
        )

    return results
