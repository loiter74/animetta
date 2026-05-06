"""
Chroma vector storage layer.

Responsibilities:
- Store and retrieve embeddings for text chunks
- Semantic similarity search (cosine distance)
- Batch deletion by file path

Replaces the role of sqlite-vec in OpenClaw, using Chroma for better vector search capabilities.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from ..models.base import Chunk

logger = logging.getLogger(__name__)

from chromadb import EmbeddingFunction, Embeddings

class _PassthroughEmbeddingFunction(EmbeddingFunction):
    """Placeholder; actual embeddings are provided externally, not via this function"""
    def __call__(self, input):
        raise NotImplementedError("Embeddings must be provided externally")
    
class ChromaStore:
    """Chroma vector database wrapper."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str = "memory_chunks",
        embedding_dim: int = 512,
        embedding_function: Any | None = None,
    ):
        """
        Initialize Chroma client.

        Args:
            persist_dir: Persistence directory
            collection_name: Collection name
            embedding_dim: Embedding vector dimension
            embedding_function: Chroma EmbeddingFunction instance.
                If None, embeddings must be provided manually during upsert.
        """
        logger.info(f"[ChromaStore] >>> Initializing: persist_dir={persist_dir}, collection={collection_name}")
        self.embedding_dim = embedding_dim
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"[ChromaStore] Persistence directory confirmed: {persist_dir}")

        logger.info(f"[ChromaStore] Creating PersistentClient...")
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        logger.info(f"[ChromaStore] ✅ PersistentClient created")

        # Dimension check: verify existing collection's embedding dimension matches
        try:
            existing = self.client.get_collection(collection_name)
            if existing.count() > 0:
                existing_dim = None
                # Method 1: peek
                sample = existing.peek(limit=1)
                if sample.get("embeddings") and len(sample["embeddings"]) > 0:
                    existing_dim = len(sample["embeddings"][0])
                # Method 2: get one record
                if existing_dim is None:
                    got = existing.get(limit=1, include=["embeddings"])
                    if got.get("embeddings") and len(got["embeddings"]) > 0:
                        existing_dim = len(got["embeddings"][0])

                if existing_dim is not None and existing_dim != embedding_dim:
                    logger.warning(
                        f"Chroma collection '{collection_name}' dimension mismatch: "
                        f"existing={existing_dim}, expected={embedding_dim}. "
                        f"Deleting and recreating..."
                    )
                    self.client.delete_collection(collection_name)
        except Exception as e:
            logger.debug(f"Chroma dimension check skipped: {e}")

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # Cosine distance
            embedding_function=_PassthroughEmbeddingFunction(),
        )
        logger.info(
            f"Chroma collection '{collection_name}' ready (dim={embedding_dim}), "
            f"{self.collection.count()} vectors stored"
        )

    def upsert_chunks(
        self,
        chunks: list[Chunk],
        sqlite_rowids: list[int],
        embeddings: list[list[float]] | None = None,
    ):
        """
        Batch upsert chunks to Chroma.

        Uses SQLite rowid as the Chroma document ID to keep both sides consistent.

        Args:
            chunks: List of text chunks
            sqlite_rowids: Corresponding SQLite rowid list
            embeddings: Pre-computed embedding vectors. Can be None if the
                collection has an embedding_function.
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
                "oral_version": c.oral_version or "",  # Colloquial version
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
        """Delete all vectors under a given file path."""
        self.collection.delete(where={"path": path})

    def vector_search(
        self,
        query_text: str | None = None,
        query_embedding: list[float] | None = None,
        n_results: int = 24,
        where: dict | None = None,
    ) -> list[tuple[str, float, dict]]:
        """
        Vector semantic search.

        Returns:
            [(chroma_id, distance, metadata), ...] — smaller distance means more similar (cosine distance).
            metadata includes oral_version and other fields.
            Note: Chroma returns distance, not similarity. Convert via: similarity = 1 - distance
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
        if results["ids"] and results["distances"] and results["metadatas"]:
            for doc_id, dist, meta in zip(results["ids"][0], results["distances"][0], results["metadatas"][0]):
                pairs.append((doc_id, dist, meta or {}))
        return pairs

    def count(self) -> int:
        return self.collection.count()
