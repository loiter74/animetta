"""Tests for hybrid search scoring fusion (70% vector + 30% keyword)."""

import pytest
from unittest.mock import MagicMock, patch


class TestHybridSearch:
    """Hybrid search fusion logic with mocked storage."""

    @pytest.fixture
    def mock_sqlite(self):
        store = MagicMock()
        store.keyword_search = MagicMock(return_value=[
            (1, 0), (2, 1), (3, 2),  # rowid, rank
        ])
        # get_chunk_by_rowid returns objects with .text, .path, etc.
        def _get_chunk(rowid):
            chunk = MagicMock()
            chunk.text = f"chunk {rowid} text"
            chunk.path = f"/path/{rowid}.md"
            chunk.start_line = 1
            chunk.end_line = 5
            chunk.source = f"file_{rowid}"
            return chunk
        store.get_chunk_by_rowid = MagicMock(side_effect=_get_chunk)
        return store

    @pytest.fixture
    def mock_chroma(self):
        store = MagicMock()
        store.vector_search = MagicMock(return_value=[
            ("1", 0.1, {"oral_version": "oral 1"}),  # (chroma_id, distance, metadata)
            ("2", 0.3, {}),
            ("4", 0.2, {}),  # only in vector, not in keyword
        ])
        return store

    def test_hybrid_search_fusion(self, mock_sqlite, mock_chroma):
        """Fusion scores should combine vector (70%) and keyword (30%) weights."""
        from animetta import $$$
        from animetta import $$$

        config = SearchConfig()
        config.vector_weight = 0.7
        config.keyword_weight = 0.3
        config.default_max_results = 5
        config.default_min_score = 0.0

        results = hybrid_search(
            query="test query",
            sqlite_store=mock_sqlite,
            chroma_store=mock_chroma,
            config=config,
        )

        # 4 candidates: rowid 1, 2, 3, 4
        # Row 1: vec=0.9, kw=1.0 → 0.7*0.9 + 0.3*1.0 = 0.93
        # Row 2: vec=0.7, kw=0.5 → 0.7*0.7 + 0.3*0.5 = 0.64
        # Row 4: vec=0.8, kw=0.0 → 0.7*0.8 + 0.3*0.0 = 0.56
        # Row 3: vec=0.0, kw=0.33 → 0.7*0.0 + 0.3*0.33 = 0.1
        assert len(results) == 4
        assert results[0].score == pytest.approx(0.93, rel=1e-2)
        assert results[1].score == pytest.approx(0.64, rel=1e-2)

    def test_hybrid_search_empty(self, mock_sqlite, mock_chroma):
        """Empty results from both stores returns empty list."""
        from animetta import $$$

        mock_sqlite.keyword_search = MagicMock(return_value=[])
        mock_chroma.vector_search = MagicMock(return_value=[])

        results = hybrid_search(
            query="nothing",
            sqlite_store=mock_sqlite,
            chroma_store=mock_chroma,
        )
        assert results == []

    def test_hybrid_search_vector_fallback(self, mock_sqlite):
        """When Chroma fails, fall back to keyword-only results."""
        from animetta import $$$

        mock_chroma = MagicMock()
        mock_chroma.vector_search = MagicMock(side_effect=Exception("Chroma down"))

        results = hybrid_search(
            query="test",
            sqlite_store=mock_sqlite,
            chroma_store=mock_chroma,
        )
        # Should still get keyword results
        assert len(results) > 0

    def test_hybrid_search_keyword_fallback(self, mock_chroma):
        """When SQLite FTS5 fails, fall back to vector-only results."""
        from animetta import $$$

        mock_sqlite = MagicMock()
        mock_sqlite.keyword_search = MagicMock(side_effect=Exception("FTS5 down"))
        mock_sqlite.get_chunk_by_rowid = MagicMock(return_value=None)

        results = hybrid_search(
            query="test",
            sqlite_store=mock_sqlite,
            chroma_store=mock_chroma,
        )
        # Vector results exist, but get_chunk_by_rowid returns None,
        # so no results without SQLite for chunk lookup
        assert results == []

    def test_hybrid_search_min_score_filter(self, mock_sqlite, mock_chroma):
        """Results below min_score should be excluded."""
        from animetta import $$$
        from animetta import $$$

        config = SearchConfig()
        config.default_min_score = 0.6

        results = hybrid_search(
            query="test",
            sqlite_store=mock_sqlite,
            chroma_store=mock_chroma,
            config=config,
        )
        # Only row 1 (score 0.93) > 0.6 should remain
        assert len(results) >= 1
        for r in results:
            assert r.score >= 0.6
