"""Tests for Chroma upsert with None embeddings and embedding fallback."""

import os, sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


class TestChromaUpsertFallback:
    """When embeddings are None, Chroma should skip upsert gracefully."""

    def test_upsert_skips_when_no_embeddings(self):
        """upsert_chunks with embeddings=None should not call collection.upsert."""
        from anima.memory.storage.chroma import ChromaStore
        from anima.memory.models.base import Chunk

        store = ChromaStore.__new__(ChromaStore)
        store.collection = MagicMock()

        chunks = [
            Chunk(text="hello", path="test.md", source="test",
                  start_line=1, end_line=1, content_hash="abc", chunk_index=0)
        ]
        rowids = [1]

        store.upsert_chunks(chunks, rowids, embeddings=None)

        # Should NOT call collection.upsert when embeddings is None
        store.collection.upsert.assert_not_called()

    def test_upsert_calls_when_embeddings_provided(self):
        """upsert_chunks with embeddings should call collection.upsert."""
        from anima.memory.storage.chroma import ChromaStore
        from anima.memory.models.base import Chunk

        store = ChromaStore.__new__(ChromaStore)
        store.collection = MagicMock()

        chunks = [
            Chunk(text="hello", path="test.md", source="test",
                  start_line=1, end_line=1, content_hash="abc", chunk_index=0)
        ]
        rowids = [1]
        emb = [[0.1] * 512]

        store.upsert_chunks(chunks, rowids, embeddings=emb)

        # Should call collection.upsert
        store.collection.upsert.assert_called_once()


class TestEmbeddingFallback:
    """MemoryManager should fall back gracefully when embedding model fails."""

    def test_manager_creates_without_embedding(self, tmp_path):
        """MemoryManager should initialize even when embedding is unavailable."""
        from anima.memory.manager import MemoryManager
        from anima.memory.config import MemoryConfig

        config = MemoryConfig(
            workspace_dir=str(tmp_path / "ws"),
            db_path=str(tmp_path / "memory.sqlite"),
            chroma_path=str(tmp_path / "chroma"),
        )
        mgr = MemoryManager(config=config)
        results = mgr.search("test")
        assert isinstance(results, list), "Search should return a list"
