"""Tests for WikiOrganizer — page organization pipeline with mocked LLM."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from animetta.memory.wiki.models import PageType, WikiPage
from animetta.memory.wiki.organizer import WikiOrganizer


@pytest.fixture
def wiki_with_pages():
    """WikiManager with a few test pages."""
    wiki = MagicMock()
    wiki._wiki_dir = MagicMock()
    wiki.list_pages.return_value = [
        "entities/user.md",
        "concepts/likes.md",
        "entities/project.md",
    ]

    def mock_read_page(rel):
        pages = {
            "entities/user.md": WikiPage(
                title="User",
                page_type=PageType.ENTITY,
                path="entities/user.md",
                content="用户叫小明",
                tags=["user", "person"],
                links=[],
            ),
            "concepts/likes.md": WikiPage(
                title="Likes",
                page_type=PageType.CONCEPT,
                path="concepts/likes.md",
                content="喜欢编程和音乐",
                tags=["user", "interest"],
                links=["entities/user.md"],
            ),
            "entities/project.md": WikiPage(
                title="Project",
                page_type=PageType.ENTITY,
                path="entities/project.md",
                content="Anima project",
                tags=["project"],
                links=[],
            ),
        }
        return pages.get(rel)

    wiki.read_page.side_effect = mock_read_page
    wiki.page_exists.return_value = False
    return wiki


class TestWikiOrganizer:
    """WikiOrganizer — collection, graph, suggestions, application."""

    def test_collect_pages(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        pages = org._collect_pages()
        assert len(pages) == 3
        assert "entities/user.md" in pages
        assert "concepts/likes.md" in pages

    def test_build_graph(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        pages = org._collect_pages()
        graph = org._build_graph(pages)
        assert "tag_groups" in graph
        assert "links" in graph
        assert "backlinks" in graph

    def test_build_graph_finds_tag_groups(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        pages = org._collect_pages()
        graph = org._build_graph(pages)
        # "user" tag appears in entities/user.md AND concepts/likes.md
        assert "user" in graph["tag_groups"]
        assert len(graph["tag_groups"]["user"]) == 2

    def test_format_pages_summary(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        pages = org._collect_pages()
        summary = org._format_pages_summary(pages)
        assert "entities/user.md" in summary
        assert "user" in summary

    def test_rule_based_suggestions_creates_synthesis(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        pages = org._collect_pages()
        graph = org._build_graph(pages)
        suggestions = org._rule_based_suggestions(pages, graph)
        assert "synthesis" in suggestions
        assert "updates" in suggestions

    def test_rule_based_suggestions_finds_missing_backlinks(self, wiki_with_pages):
        """entities/user.md is linked from concepts/likes.md but has no backlink."""
        org = WikiOrganizer(wiki_with_pages)
        pages = org._collect_pages()
        graph = org._build_graph(pages)
        suggestions = org._rule_based_suggestions(pages, graph)
        # user.md should get an update adding concepts/likes.md backlink
        updates = suggestions["updates"]
        user_updates = [u for u in updates if "entities/user.md" in u["path"]]
        assert len(user_updates) > 0

    def test_apply_merge_creates_synthesis_page(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        merge = {
            "sources": ["entities/user.md", "concepts/likes.md"],
            "target": "synthesis/user-summary.md",
            "title": "用户综合",
            "reason": "相关主题",
        }
        result = org._apply_merge(merge)
        assert result is True
        wiki_with_pages.write_page.assert_called()
        wiki_with_pages.append_log.assert_called_with(
            "merge", "synthesis/user-summary.md", "from: entities/user.md, concepts/likes.md"
        )

    def test_apply_merge_skips_existing_target(self, wiki_with_pages):
        wiki_with_pages.page_exists.return_value = True
        org = WikiOrganizer(wiki_with_pages)
        result = org._apply_merge({"sources": ["a.md"], "target": "existing.md", "title": "X", "reason": ""})
        assert result is False

    def test_apply_merge_empty_sources(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        assert org._apply_merge({"sources": [], "target": "t.md", "title": "T"}) is False

    def test_apply_synthesis_creates_page(self, wiki_with_pages):
        org = WikiOrganizer(wiki_with_pages)
        synth = {
            "path": "synthesis/new-topic.md",
            "title": "新话题",
            "source_pages": ["entities/user.md"],
            "summary": "综合摘要",
        }
        result = org._apply_synthesis(synth)
        assert result is True
        wiki_with_pages.write_page.assert_called()

    def test_apply_synthesis_existing_skips(self, wiki_with_pages):
        wiki_with_pages.page_exists.return_value = True
        org = WikiOrganizer(wiki_with_pages)
        result = org._apply_synthesis({"path": "existing.md", "title": "X", "source_pages": [], "summary": ""})
        assert result is False

    def test_apply_update_adds_links(self, wiki_with_pages):
        user_page = WikiPage(
            title="User",
            page_type=PageType.ENTITY,
            path="entities/user.md",
            content="Hello",
            links=[],
        )
        # Override the side_effect set by fixture
        wiki_with_pages.read_page.side_effect = None
        wiki_with_pages.read_page.return_value = user_page

        org = WikiOrganizer(wiki_with_pages)
        upd = {
            "path": "entities/user.md",
            "add_links": ["concepts/likes.md"],
            "reason": "补充关联",
        }
        result = org._apply_update(upd)
        assert result is True
        # Should have been written back with updated links (stemmed from path)
        written_page = wiki_with_pages.write_page.call_args[0][0]
        assert "likes" in written_page.links

    def test_apply_update_no_changes_for_existing_link(self, wiki_with_pages):
        """When the stemmed link already exists, no update happens."""
        user_page = WikiPage(
            title="User",
            page_type=PageType.ENTITY,
            path="entities/user.md",
            content="Hello",
            links=["likes"],  # stemmed form already present
        )
        # Override the side_effect set by fixture
        wiki_with_pages.read_page.side_effect = None
        wiki_with_pages.read_page.return_value = user_page

        org = WikiOrganizer(wiki_with_pages)
        upd = {
            "path": "entities/user.md",
            "add_links": ["concepts/likes.md"],  # stem = "likes", already in links
            "reason": "already there",
        }
        result = org._apply_update(upd)
        assert result is False  # no change

    @pytest.mark.asyncio
    async def test_organize_with_llm(self, wiki_with_pages):
        """organize() with mocked LLM client returning valid JSON."""
        llm = AsyncMock()
        llm.chat = AsyncMock(return_value='{"merges": [], "synthesis": [], "updates": []}')

        wiki_with_pages.list_pages.return_value = ["entities/user.md"]
        wiki_with_pages.read_page.return_value = WikiPage(
            title="User", page_type=PageType.ENTITY, path="entities/user.md", content="test"
        )

        org = WikiOrganizer(wiki_with_pages, llm_client=llm)
        result = await org.organize()
        assert result["merges"] == 0
        assert result["synthesis"] == 0
        assert result["updates"] == 0

    @pytest.mark.asyncio
    async def test_organize_no_llm_fallsback_to_rule_based(self, wiki_with_pages):
        """Without LLM client, organize() uses rule-based fallback."""
        org = WikiOrganizer(wiki_with_pages, llm_client=None)
        result = await org.organize()
        # Should return result dict without crashing
        assert isinstance(result, dict)
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_organize_progress_callback(self, wiki_with_pages):
        llm = AsyncMock()
        llm.chat = AsyncMock(return_value='{"merges": [], "synthesis": [], "updates": []}')

        org = WikiOrganizer(wiki_with_pages, llm_client=llm)
        callback = AsyncMock()
        await org.organize(progress_callback=callback)
        assert callback.called

    def test_summarize_result(self):
        result = {"merges": 2, "synthesis": 1, "updates": 3, "errors": []}
        summary = WikiOrganizer._summarize_result(result)
        assert "2 merged" in summary
        assert "1 synthesis" in summary

    def test_summarize_result_no_changes(self):
        summary = WikiOrganizer._summarize_result({"merges": 0, "synthesis": 0, "updates": 0, "errors": []})
        assert summary == "no changes"
