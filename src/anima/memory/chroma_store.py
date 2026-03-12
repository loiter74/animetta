"""
Chroma 向量存储层.

负责:
- 存储和检索文本块的 embedding
- 语义相似度搜索 (余弦距离)
- 按文件路径批量删除

替代 OpenClaw 中 sqlite-vec 的角色, 用 Chroma 获得更好的向量检索能力.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from .models import Chunk

logger = logging.getLogger(__name__)


class ChromaStore:
    """Chroma 向量数据库封装."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str = "memory_chunks",
        embedding_function: Any | None = None,
    ):
        """
        初始化 Chroma 客户端.

        Args:
            persist_dir: 持久化目录
            collection_name: 集合名称
            embedding_function: Chroma 的 EmbeddingFunction 实例.
                如果为 None, 需要在 upsert 时手动传入 embeddings.
        """
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # 余弦距离
            embedding_function=embedding_function,
        )
        logger.info(
            f"Chroma collection '{collection_name}' ready, "
            f"{self.collection.count()} vectors stored"
        )

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        sqlite_rowids: list[int],
        embeddings: list[list[float]] | None = None,
    ):
        """
        批量 upsert 块到 Chroma.

        使用 SQLite rowid 作为 Chroma 的文档 ID, 保持两边一致.

        Args:
            chunks: 文本块列表
            sqlite_rowids: 对应的 SQLite rowid 列表
            embeddings: 预计算的 embedding 向量. 如果 collection 有
                embedding_function 则可为 None.
        """
        if not chunks:
            return

        ids = [str(rid) for rid in sqlite_rowids]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "path": c.path,
                "source": c.source,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "content_hash": c.content_hash,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        kwargs: dict[str, Any] = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }
        if embeddings is not None:
            kwargs["embeddings"] = embeddings

        self.collection.upsert(**kwargs)
        logger.debug(f"Upserted {len(chunks)} chunks to Chroma")

    def delete_by_path(self, path: str):
        """删除某文件路径下的所有向量."""
        self.collection.delete(where={"path": path})

    def vector_search(
        self,
        query_text: str | None = None,
        query_embedding: list[float] | None = None,
        n_results: int = 24,
        where: dict | None = None,
    ) -> list[tuple[str, float]]:
        """
        向量语义搜索.

        Returns:
            [(chroma_id, distance), ...] — distance 越小越相似 (余弦距离).
            注意: Chroma 返回的是距离而非相似度, 需要转换: similarity = 1 - distance
        """
        kwargs: dict[str, Any] = {"n_results": n_results}
        if query_text is not None:
            kwargs["query_texts"] = [query_text]
        elif query_embedding is not None:
            kwargs["query_embeddings"] = [query_embedding]
        else:
            raise ValueError("Must provide query_text or query_embedding")

        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        pairs = []
        if results["ids"] and results["distances"]:
            for doc_id, dist in zip(results["ids"][0], results["distances"][0]):
                pairs.append((doc_id, dist))
        return pairs

    def count(self) -> int:
        return self.collection.count()
