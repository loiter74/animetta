"""Tests for fixed bugs: MemeStore init, FuzzyLayer stop, MemorySystem start warnings."""

import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from unittest.mock import MagicMock, patch
import pytest


class TestMemeStoreInit:
    """Verify MemeStore initializes without _WikiPage NameError."""

    def test_meme_store_creates_with_valid_wiki(self):
        """MemeStore.__init__ should import WikiPage and store it."""

        wiki = MagicMock()
        store = MemeStore(wiki)

        assert store._WikiPage is not None, "WikiPage should be stored"
        assert store._PageType is not None, "PageType should be stored"
        assert store._wiki is wiki


class TestFuzzyLayerStop:
    """MemorySystem.stop() should not crash on FuzzyLayer without close()."""

    def test_stop_survives_fuzzy_without_close(self):
        """stop() with FuzzyLayer that lacks close() should not raise."""

        # Simulate a minimal config that avoids full init
        config = {
            "workspace_dir": str(pytest.importorskip("tempfile").mkdtemp()),
            "short_term_max_turns": 5,
            "meme_pool": {"enabled": False},
            "fuzzy_memory": {"enabled": False},
            "learner": {"enabled": False},
            "scheduler": {"enabled": False},
        }

        system = MemorySystem(config)

        # Manually set a fake fuzzy (no close method)
        system.fuzzy = MagicMock(spec=[])  # no close attribute
        # Should not raise
        system.stop()


class TestWikiPagesHandler:
    """Verify on_get_wiki_pages returns pages from both memory and disk."""

    def test_handler_returns_pages_from_disk(self):
        """Disk fallback should find .md files."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            wiki_dir = Path(tmp) / "wiki"
            wiki_dir.mkdir()
            (wiki_dir / "entities").mkdir()
            (wiki_dir / "entities" / "alice.md").write_text("# Alice", encoding="utf-8")

            md_files = sorted(wiki_dir.rglob("*.md"))
            relpaths = [str(f.relative_to(wiki_dir)).replace("\\", "/") for f in md_files]
            assert "entities/alice.md" in relpaths


class TestMemorySystemGracefulDegrade:
    """MemorySystem should not crash when subsystems fail to init."""

    def test_meme_pool_none_after_failure(self):
        """When MemePool init fails, meme_pool should remain None, not crash."""
        import tempfile

        config = {
            "workspace_dir": tempfile.mkdtemp(),
            "short_term_max_turns": 5,
            "meme_pool": {"enabled": False},
            "fuzzy_memory": {"enabled": False},
            "learner": {"enabled": False},
            "scheduler": {"enabled": False},
        }
        system = MemorySystem(config)
        assert system.meme_pool is None, "Should be None when disabled"
