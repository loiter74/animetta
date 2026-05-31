"""Tests for MemoryManager — index/sync operations, search, flush."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from animetta.memory.config import MemoryConfig
from animetta.memory.manager import MemoryManager


@pytest.fixture
def mock_config(tmp_path):
    return MemoryConfig(workspace_dir=str(tmp_path / "workspace"))


@pytest.fixture
def manager(mock_config):
    """Create a MemoryManager with mocked storage backends."""
    with (
        patch("animetta.memory.manager.SQLiteStore") as mock_sqlite,
        patch("animetta.memory.manager.ChromaStore") as mock_chroma,
        patch("animetta.memory.manager.MemoryEntryStore") as mock_entry,
        patch("sentence_transformers.SentenceTransformer") as mock_st,
    ):
        mock_sqlite_instance = MagicMock()
        mock_sqlite_instance.conn = MagicMock()
        mock_sqlite.return_value = mock_sqlite_instance
        mock_chroma.return_value = MagicMock()
        mock_entry.return_value = MagicMock()

        mock_embedder = MagicMock()
        # encode() returns a list of numpy arrays (each has .tolist())
        import numpy as np
        mock_embedder.encode.return_value = [np.array([0.1, 0.2, 0.3])]
        mock_st.return_value = mock_embedder

        mgr = MemoryManager(config=mock_config)
        yield mgr


class TestMemoryManagerInit:
    """MemoryManager construction."""

    def test_creates_workspace_dir(self, tmp_path):
        ws = tmp_path / "new_workspace"
        config = MemoryConfig(workspace_dir=str(ws))
        with (
            patch("animetta.memory.manager.SQLiteStore") as ms,
            patch("animetta.memory.manager.ChromaStore") as mc,
            patch("animetta.memory.manager.MemoryEntryStore") as me,
            patch("sentence_transformers.SentenceTransformer"),
        ):
            ms.return_value = MagicMock()
            ms.return_value.conn = MagicMock()
            mc.return_value = MagicMock()
            me.return_value = MagicMock()
            MemoryManager(config=config)
        assert ws.exists()

    def test_resolves_paths(self, tmp_path):
        ws = tmp_path / "ws"
        config = MemoryConfig(workspace_dir=str(ws))
        with (
            patch("animetta.memory.manager.SQLiteStore") as ms,
            patch("animetta.memory.manager.ChromaStore") as mc,
            patch("animetta.memory.manager.MemoryEntryStore") as me,
            patch("sentence_transformers.SentenceTransformer"),
        ):
            ms.return_value = MagicMock()
            ms.return_value.conn = MagicMock()
            mc.return_value = MagicMock()
            me.return_value = MagicMock()
            mgr = MemoryManager(config=config)
        assert mgr.config.db_path is not None
        assert mgr.config.chroma_path is not None

    def test_close_calls_sqlite_close(self, manager):
        manager.close()
        manager.sqlite.close.assert_called_once()


class TestMemoryManagerGet:
    """Reading files via manager.get()."""

    def test_get_existing_file(self, manager, tmp_path):
        ws = Path(manager.config.workspace_dir)
        f = ws / "test.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("hello\nworld", encoding="utf-8")
        content = manager.get("test.md")
        assert content == "hello\nworld"

    def test_get_nonexistent_returns_empty(self, manager):
        assert manager.get("nope.md") == ""

    def test_get_with_line_range(self, manager, tmp_path):
        ws = Path(manager.config.workspace_dir)
        f = ws / "lines.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("a\nb\nc\nd\ne", encoding="utf-8")
        content = manager.get("lines.md", start_line=2, end_line=4)
        assert content == "b\nc\nd"


class TestMemoryManagerSync:
    """Sync indexing workflow."""

    def test_sync_no_files(self, manager):
        """Sync with empty workspace should not crash."""
        manager.sync()
        # No files to index -> 0 indexed

    def test_sync_indexes_md_files(self, manager, tmp_path):
        ws = Path(manager.config.workspace_dir)
        raw = ws / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        (raw / "2026-05-10.md").write_text("# Daily\ncontent", encoding="utf-8")

        # mock _index_file to return True
        manager._index_file = MagicMock(return_value=True)  # type: ignore[method-assign]

        manager.sync()
        manager._index_file.assert_called()  # type: ignore[attr-defined]

    def test_sync_wiki_directory(self, manager, tmp_path):
        ws = Path(manager.config.workspace_dir)
        wiki = ws / "wiki" / "entities"
        wiki.mkdir(parents=True, exist_ok=True)
        (wiki / "user.md").write_text("# User", encoding="utf-8")

        manager._index_file = MagicMock(return_value=True)  # type: ignore[method-assign]
        manager.sync()
        # Should find at least the wiki/entities/user.md
        calls = [c[0][0] for c in manager._index_file.call_args_list]  # type: ignore[attr-defined]
        assert any("user.md" in c for c in calls)

    def test_index_file_skips_unchanged(self, manager, tmp_path):
        # Mock sqlite to simulate previously indexed file with same hash
        manager.sqlite.get_file_entry.return_value = MagicMock()
        import hashlib
        content = b"content"
        manager.sqlite.get_file_entry.return_value.file_hash = (
            hashlib.sha256(content).hexdigest()
        )

        ws = Path(manager.config.workspace_dir)
        f = ws / "test.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(content)

        result = manager._index_file("test.md", "raw")
        assert result is False  # unchanged, not indexed


class TestMemoryManagerSearch:
    """Search delegation."""

    @patch("animetta.memory.manager.hybrid_search")
    def test_search_calls_hybrid(self, mock_hybrid, manager):
        mock_hybrid.return_value = []
        manager.search("test query")
        mock_hybrid.assert_called_once()
        args, kwargs = mock_hybrid.call_args
        assert kwargs["query"] == "test query"

    @patch("animetta.memory.manager.hybrid_search")
    def test_search_passes_max_results(self, mock_hybrid, manager):
        mock_hybrid.return_value = []
        manager.search("q", max_results=5, min_score=0.2)
        assert mock_hybrid.call_args[1]["max_results"] == 5
        assert mock_hybrid.call_args[1]["min_score"] == 0.2


class TestMemoryManagerFlush:
    """Flush decision logic."""

    def test_should_flush_disabled(self, manager):
        manager.config.flush_enabled = False
        assert manager.should_flush(100000, 128000) is False

    def test_should_flush_true_when_over_threshold(self, manager):
        # threshold = 128000 - 20000 - 4000 = 104000
        assert manager.should_flush(105000, 128000) is True

    def test_should_flush_false_when_under_threshold(self, manager):
        assert manager.should_flush(1000, 128000) is False
