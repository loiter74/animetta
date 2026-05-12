"""Tests for MemeStore — wiki-backed CRUD operations."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.anima.memory.meme.models import CognitiveAnalysis, Meme, MemeSource
from src.anima.memory.meme.store import MemeStore


@pytest.fixture
def mock_wiki():
    """WikiManager with mocked CRUD."""
    wiki = MagicMock()
    wiki._wiki_dir = MagicMock()
    wiki.list_pages.return_value = []
    wiki.read_page.return_value = None
    return wiki


@pytest.fixture
def store(mock_wiki):
    return MemeStore(wiki=mock_wiki)


class TestMemeStore:
    """MemeStore CRUD operations."""

    def test_insert_returns_id(self, store, mock_wiki):
        meme = Meme(text="测试梗")
        result = store.insert(meme)
        assert result == meme.id
        mock_wiki.write_page.assert_called_once()

    def test_update_writes_page(self, store, mock_wiki):
        meme = Meme(id="meme_001", text="update test")
        store.update(meme)
        mock_wiki.write_page.assert_called_once()

    def test_get_returns_none_for_missing(self, store, mock_wiki):
        mock_wiki.read_page.return_value = None
        result = store.get("nonexistent")
        assert result is None

    def test_get_returns_meme(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        mock_wiki.read_page.return_value = WikiPage(
            title="test",
            page_type=PageType.MEME,
            path="memes/meme_001.md",
            content="梗内容",
            metadata={
                "id": "meme_001",
                "context_hint": "测试",
                "source": "ai",
                "base_score": 0.8,
                "current_score": 0.7,
                "use_count": 2,
                "is_active": True,
                "resurrection_count": 0,
                "source_platform": "internal",
                "review_status": "pending",
                "last_used_at": None,
            },
            tags=["test"],
        )

        meme = store.get("meme_001")
        assert meme is not None
        assert meme.id == "meme_001"
        assert meme.text == "梗内容"
        assert meme.base_score == 0.8
        assert meme.use_count == 2

    def test_get_active_filters(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        # Two pages: one active, one inactive
        mock_wiki.list_pages.return_value = [
            "memes/meme_active.md",
            "memes/meme_inactive.md",
        ]

        active_page = WikiPage(
            title="active",
            page_type=PageType.MEME,
            path="memes/meme_active.md",
            content="active meme",
            metadata={"id": "active", "is_active": True, "source": "ai", "current_score": 0.9},
        )
        inactive_page = WikiPage(
            title="inactive",
            page_type=PageType.MEME,
            path="memes/meme_inactive.md",
            content="inactive meme",
            metadata={"id": "inactive", "is_active": False, "source": "ai", "current_score": 0.5},
        )

        mock_wiki.read_page.side_effect = [active_page, inactive_page]
        active = store.get_active(limit=10)
        assert len(active) == 1
        assert active[0].id == "active"

    def test_get_inactive_filters(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        mock_wiki.list_pages.return_value = ["memes/meme_01.md"]
        mock_wiki.read_page.return_value = WikiPage(
            title="x",
            page_type=PageType.MEME,
            path="memes/meme_01.md",
            content="x",
            metadata={"id": "m1", "is_active": False, "source": "ai", "current_score": 0.3},
        )

        inactive = store.get_inactive(limit=10)
        assert len(inactive) == 1

    def test_update_score(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        page = WikiPage(
            title="x",
            page_type=PageType.MEME,
            path="memes/meme_01.md",
            content="x",
            metadata={"id": "m1", "is_active": True, "source": "ai"},
        )
        mock_wiki.read_page.return_value = page

        store.update_score("meme_01", 0.5)
        assert page.metadata["current_score"] == 0.5

    def test_increment_use(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        page = WikiPage(
            title="x",
            page_type=PageType.MEME,
            path="memes/meme_01.md",
            content="x",
            metadata={"id": "m1", "is_active": True, "source": "ai", "use_count": 3},
        )
        mock_wiki.read_page.return_value = page

        store.increment_use("meme_01")
        assert page.metadata["use_count"] == 4

    def test_set_active(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        page = WikiPage(
            title="x",
            page_type=PageType.MEME,
            path="memes/meme_01.md",
            content="x",
            metadata={"id": "m1", "is_active": True, "source": "ai"},
        )
        mock_wiki.read_page.return_value = page

        store.set_active("meme_01", False)
        assert page.metadata["is_active"] is False

    def test_delete_removes_file(self, store):
        """Delete delegates to wiki directory file unlink."""
        wiki = MagicMock()
        wiki._wiki_dir = MagicMock()
        store._wiki = wiki
        # __truediv__ is called twice: dir/"memes"/"id.md"
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.__truediv__.return_value = mock_dir  # chain: a/b/c → same mock
        wiki._wiki_dir.__truediv__.return_value = mock_dir

        store.delete("meme_001")
        mock_dir.unlink.assert_called_once()

    def test_count_active(self, store, mock_wiki):
        mock_wiki.list_pages.return_value = ["memes/a.md", "memes/b.md"]
        mock_wiki.read_page.return_value = MagicMock()
        mock_wiki.read_page.return_value.metadata = {"id": "x", "is_active": True, "source": "ai"}
        mock_wiki.read_page.return_value = MagicMock()
        mock_wiki.read_page.return_value.metadata = {"id": "y", "is_active": True, "source": "ai"}

        count = store.count_active()
        assert count == 2

    def test_compat_layer_list_active(self, store, mock_wiki):
        mock_wiki.list_pages.return_value = []
        assert store.list_active() == []

    def test_compat_layer_save(self, store, mock_wiki):
        meme = Meme(text="save test")
        result = store.save(meme)
        assert result == meme.id

    def test_compat_layer_discard(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        page = WikiPage(
            title="x", page_type=PageType.MEME, path="memes/m.md", content="x",
            metadata={"id": "m1", "is_active": True, "source": "ai"},
        )
        mock_wiki.read_page.return_value = page
        store.discard("m1")
        assert page.metadata["is_active"] is False

    def test_compat_layer_resurrect(self, store, mock_wiki):
        from src.anima.memory.wiki.models import PageType, WikiPage

        page = WikiPage(
            title="x", page_type=PageType.MEME, path="memes/m.md", content="x",
            metadata={"id": "m1", "is_active": False, "source": "ai"},
        )
        mock_wiki.read_page.return_value = page
        store.resurrect("m1")
        assert page.metadata["is_active"] is True

    def test_compat_layer_list_discarded(self, store, mock_wiki):
        mock_wiki.list_pages.return_value = []
        assert store.list_discarded() == []
