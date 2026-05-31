"""Tests for WikiManager — CRUD, list, index, log, links."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from animetta.memory.wiki.manager import WikiManager
from animetta.memory.wiki.models import PageType, WikiPage


@pytest.fixture
def mock_manager():
    """MemoryManager with mocked backends."""
    with (
        patch("animetta.memory.manager.SQLiteStore") as ms,
        patch("animetta.memory.manager.ChromaStore") as mc,
        patch("animetta.memory.manager.MemoryEntryStore") as me,
    ):
        ms.return_value = MagicMock()
        ms.return_value.conn = MagicMock()
        mc.return_value = MagicMock()
        me.return_value = MagicMock()

        from animetta.memory.manager import MemoryManager
        from animetta.memory.config import MemoryConfig

        config = MagicMock(spec=MemoryConfig)
        config.workspace_dir = "/tmp/test_workspace"
        config.db_path = "/tmp/test_workspace/memory.sqlite"
        config.chroma_path = "/tmp/test_workspace/chroma_db"
        config.embedding = MagicMock()
        config.embedding.model_name = "test-model"
        config.resolve_paths.return_value = config

        mgr = MemoryManager.__new__(MemoryManager)
        mgr.config = config
        mgr.sqlite = ms.return_value
        mgr.chroma = mc.return_value
        mgr.memory_entries = me.return_value
        mgr._embedder = None
        yield mgr


@pytest.fixture
def wiki_manager(mock_manager, tmp_path):
    """WikiManager with tmp_path workspace."""
    mock_manager.config.workspace_dir = str(tmp_path)
    mock_manager.config.resolve_paths.return_value = mock_manager.config
    wm = WikiManager(mock_manager)
    return wm


class TestWikiManagerInit:
    """Bootstrap: directory creation, index, log."""

    def test_creates_directory_structure(self, tmp_path):
        mock_mgr = MagicMock()
        mock_mgr.config.workspace_dir = str(tmp_path)
        wm = WikiManager(mock_mgr)
        assert (tmp_path / "raw").exists()
        assert (tmp_path / "wiki").exists()
        assert (tmp_path / "wiki/entities").exists()
        assert (tmp_path / "wiki/concepts").exists()
        assert (tmp_path / "wiki/sources").exists()
        assert (tmp_path / "wiki/synthesis").exists()
        assert (tmp_path / "wiki/memes").exists()

    def test_creates_index_and_log(self, tmp_path):
        mock_mgr = MagicMock()
        mock_mgr.config.workspace_dir = str(tmp_path)
        wm = WikiManager(mock_mgr)
        assert (tmp_path / "wiki/index.md").exists()
        assert (tmp_path / "wiki/log.md").exists()

    def test_properties(self, wiki_manager):
        assert wiki_manager.raw_dir == Path(wiki_manager.manager.config.workspace_dir) / "raw"
        assert wiki_manager.wiki_dir == Path(wiki_manager.manager.config.workspace_dir) / "wiki"
        assert wiki_manager.manager is not None


class TestWikiManagerCRUD:
    """Page read/write/exists."""

    def test_read_nonexistent_returns_none(self, wiki_manager):
        assert wiki_manager.read_page("entities/nonexistent.md") is None

    def test_write_and_read_page(self, wiki_manager):
        page = WikiPage(
            title="User",
            page_type=PageType.ENTITY,
            path="entities/user.md",
            content="# User\n\nSome info.",
        )
        wiki_manager.write_page(page)
        loaded = wiki_manager.read_page("entities/user.md")
        assert loaded is not None
        assert loaded.title == "User"
        assert loaded.page_type == PageType.ENTITY
        assert "Some info" in loaded.content

    def test_page_exists(self, wiki_manager):
        assert wiki_manager.page_exists("entities/user.md") is False
        page = WikiPage(title="X", page_type=PageType.ENTITY, path="entities/user.md", content="x")
        wiki_manager.write_page(page)
        assert wiki_manager.page_exists("entities/user.md") is True

    def test_write_page_creates_parent_dirs(self, wiki_manager):
        page = WikiPage(
            title="Deep",
            page_type=PageType.CONCEPT,
            path="concepts/deep/nested.md",
            content="deep",
        )
        wiki_manager.write_page(page)
        assert wiki_manager.page_exists("concepts/deep/nested.md") is True


class TestWikiManagerList:
    """Listing pages."""

    def test_list_pages_empty(self, wiki_manager):
        assert wiki_manager.list_pages() == []

    def test_list_pages_by_type(self, wiki_manager):
        for i in range(3):
            page = WikiPage(
                title=f"Entity{i}",
                page_type=PageType.ENTITY,
                path=f"entities/e{i}.md",
                content=f"content{i}",
            )
            wiki_manager.write_page(page)

        pages = wiki_manager.list_pages(PageType.ENTITY)
        assert len(pages) == 3
        assert all("entities/" in p for p in pages)

    def test_list_pages_all(self, wiki_manager):
        wiki_manager.write_page(WikiPage(title="E", page_type=PageType.ENTITY, path="entities/e.md", content="e"))
        wiki_manager.write_page(WikiPage(title="C", page_type=PageType.CONCEPT, path="concepts/c.md", content="c"))
        wiki_manager.write_page(WikiPage(title="S", page_type=PageType.SOURCE, path="sources/s.md", content="s"))

        all_pages = wiki_manager.list_pages()
        assert len(all_pages) == 3

    def test_list_pages_excludes_index_and_log(self, wiki_manager):
        """index.md and log.md should not appear in list_pages()."""
        all_pages = wiki_manager.list_pages()
        assert "index.md" not in all_pages
        assert "log.md" not in all_pages

    def test_list_pages_unknown_type(self, wiki_manager):
        assert wiki_manager.list_pages(PageType.MEME) == []


class TestWikiManagerRaw:
    """Raw conversation log writes."""

    def test_write_raw_appends_to_daily_file(self, wiki_manager):
        dt = datetime(2026, 5, 10, 14, 30)
        wiki_manager.write_raw(dt, "Hello!")
        raw_path = wiki_manager.raw_dir / "2026-05-10.md"
        assert raw_path.exists()
        content = raw_path.read_text(encoding="utf-8")
        assert "14:30" in content
        assert "Hello!" in content

    def test_write_raw_appends_multiple(self, wiki_manager):
        t1 = datetime(2026, 5, 10, 10, 0)
        t2 = datetime(2026, 5, 10, 11, 0)
        wiki_manager.write_raw(t1, "First")
        wiki_manager.write_raw(t2, "Second")
        content = (wiki_manager.raw_dir / "2026-05-10.md").read_text(encoding="utf-8")
        assert content.count("## ") == 2


class TestWikiManagerIndexAndLog:
    """Rebuild index / append log."""

    def test_rebuild_index(self, wiki_manager):
        wiki_manager.write_page(WikiPage(title="A", page_type=PageType.ENTITY, path="entities/a.md", content="a"))
        wiki_manager.rebuild_index()
        index_content = (wiki_manager.wiki_dir / "index.md").read_text(encoding="utf-8")
        assert "# Wiki Index" in index_content
        assert "Entities" in index_content

    def test_append_log(self, wiki_manager):
        wiki_manager.append_log("test", "entities/user.md", "created for testing")
        log_content = (wiki_manager.wiki_dir / "log.md").read_text(encoding="utf-8")
        assert "test" in log_content
        assert "entities/user.md" in log_content


class TestWikiManagerLinks:
    """Wiki link helpers."""

    def test_extract_links(self, wiki_manager):
        text = "See [[entities/other]] and [[concepts/something]]."
        links = wiki_manager.extract_links(text)
        assert links == ["entities/other", "concepts/something"]

    def test_extract_links_empty(self, wiki_manager):
        assert wiki_manager.extract_links("No links here") == []

    def test_find_backlinks(self, wiki_manager):
        page_a = WikiPage(title="A", page_type=PageType.ENTITY, path="entities/a.md", content="links to [[entities/b]]")
        page_b = WikiPage(title="B", page_type=PageType.ENTITY, path="entities/b.md", content="content")
        wiki_manager.write_page(page_a)
        wiki_manager.write_page(page_b)

        backlinks = wiki_manager.find_backlinks("entities/b")
        assert "entities/a.md" in backlinks


class TestWikiManagerSearch:
    """Search delegation."""

    def test_search_delegates_to_manager(self, wiki_manager):
        wiki_manager.manager.search = MagicMock(return_value=["result"])
        results = wiki_manager.search("test")
        wiki_manager.manager.search.assert_called_once_with("test", max_results=10)
        assert results == ["result"]
