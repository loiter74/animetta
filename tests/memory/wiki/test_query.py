"""Tests for WikiQuery — context retrieval for LLM prompts."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from animetta import $$$
from animetta import $$$
from animetta import $$$
from animetta import $$$


@pytest.fixture
def mock_wiki():
    """Create a fully-mocked WikiManager."""
    wm = MagicMock()
    wm.read_page.return_value = None
    wm.search.return_value = []
    wm.list_pages.return_value = []
    return wm


@pytest.fixture
def query_obj(mock_wiki):
    """WikiQuery with mocked wiki."""
    return WikiQuery(wiki=mock_wiki)


@pytest.fixture
def sample_search_result():
    """A typical search result."""
    return SearchResult(
        text="**User**: 我喜欢吃火锅\n**AI**: 火锅确实很好吃呢~",
        path="sources/2026-05-10.md",
        start_line=1,
        end_line=3,
        score=0.85,
        source="wiki",
        vector_score=0.8,
        keyword_score=0.9,
    )


class TestSearch:
    """Async search delegation."""

    @pytest.mark.asyncio
    async def test_search_delegates_to_wiki(self, query_obj, mock_wiki):
        mock_wiki.search.return_value = ["result1", "result2"]
        results = await query_obj.search("test query", max_results=3)
        mock_wiki.search.assert_called_once_with("test query", max_results=3)
        assert results == ["result1", "result2"]

    @pytest.mark.asyncio
    async def test_search_uses_default_max_results(self, query_obj, mock_wiki):
        await query_obj.search("query")
        mock_wiki.search.assert_called_once_with("query", max_results=5)

    @pytest.mark.asyncio
    async def test_search_handles_error_gracefully(self, query_obj, mock_wiki):
        mock_wiki.search.side_effect = RuntimeError("search backend down")
        results = await query_obj.search("query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_min_score_param(self, query_obj, mock_wiki):
        await query_obj.search("query", min_score=0.5)
        mock_wiki.search.assert_called_once_with("query", max_results=5)


class TestLoadContext:
    """Context string building for system prompts."""

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_empty_when_no_data(self, mock_dt, query_obj):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        context = query_obj.load_context()
        assert context == ""

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_includes_today_summary(self, mock_dt, query_obj, mock_wiki):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        today_page = WikiPage(
            title="对话摘要 2026-05-10",
            page_type=PageType.SOURCE,
            path="sources/2026-05-10.md",
            content="今日对话内容...",
        )

        def read_page_side_effect(path):
            if path == "sources/2026-05-10.md":
                return today_page
            return None

        mock_wiki.read_page.side_effect = read_page_side_effect

        context = query_obj.load_context()
        assert "今日对话摘要" in context
        assert "今日对话内容..." in context

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_includes_yesterday_summary(self, mock_dt, query_obj, mock_wiki):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        yesterday_page = WikiPage(
            title="对话摘要 2026-05-09",
            page_type=PageType.SOURCE,
            path="sources/2026-05-09.md",
            content="昨日对话内容...",
        )

        def read_page_side_effect(path):
            if path == "sources/2026-05-09.md":
                return yesterday_page
            return None

        mock_wiki.read_page.side_effect = read_page_side_effect

        context = query_obj.load_context()
        assert "昨日对话摘要" in context
        assert "昨日对话内容..." in context

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_includes_both_days(self, mock_dt, query_obj, mock_wiki):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        today_page = WikiPage(
            title="today", page_type=PageType.SOURCE,
            path="sources/2026-05-10.md", content="today content",
        )
        yesterday_page = WikiPage(
            title="yesterday", page_type=PageType.SOURCE,
            path="sources/2026-05-09.md", content="yesterday content",
        )

        def read_page_side_effect(path):
            if "2026-05-10" in path:
                return today_page
            if "2026-05-09" in path:
                return yesterday_page
            return None

        mock_wiki.read_page.side_effect = read_page_side_effect

        context = query_obj.load_context()
        assert "今日对话摘要" in context
        assert "昨日对话摘要" in context
        assert "today content" in context
        assert "yesterday content" in context

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_with_search_query(self, mock_dt, query_obj, mock_wiki):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        sr = SearchResult(
            text="找到的记忆内容",
            path="entities/user.md",
            start_line=1, end_line=1,
            score=0.9, source="wiki",
        )
        mock_wiki.search.return_value = [sr]

        context = query_obj.load_context(query="用户偏好", max_results=3)
        mock_wiki.search.assert_called_once_with("用户偏好", max_results=3)
        assert "相关记忆" in context

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_search_error_is_handled(self, mock_dt, query_obj, mock_wiki):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        mock_wiki.search.side_effect = RuntimeError("search failed")

        # Should not raise
        context = query_obj.load_context(query="test")
        assert "相关记忆" not in context

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_wiki_formats_score(self, mock_dt, query_obj, mock_wiki):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        sr = SearchResult(
            text="sample text",
            path="entities/x.md",
            start_line=0, end_line=1,
            score=0.75, source="wiki",
        )
        mock_wiki.search.return_value = [sr]

        context = query_obj.load_context(query="x")
        assert "score=0.75" in context

    @patch("anima.memory.wiki.query.datetime")
    def test_load_context_truncates_search_results(self, mock_dt, query_obj, mock_wiki):
        mock_dt.now.return_value = datetime(2026, 5, 10, 14, 0)
        results = [
            SearchResult(
                text=f"result {i}", path=f"path/{i}.md",
                start_line=0, end_line=1,
                score=0.9 - i * 0.1, source="wiki",
            )
            for i in range(10)
        ]
        mock_wiki.search.return_value = results

        context = query_obj.load_context(query="x", max_results=3)
        # Only first 3 should appear
        assert "result 0" in context
        assert "result 1" in context
        assert "result 2" in context
        assert str(results) != context  # not all visible, truncated


class TestSearchTurns:
    """Converting search results to MemoryTurn objects."""

    def test_search_turns_returns_empty_list_on_error(self, query_obj, mock_wiki):
        mock_wiki.search.side_effect = RuntimeError("search error")
        turns = query_obj.search_turns("query", "sess-1")
        assert turns == []

    def test_search_turns_converts_results(self, query_obj, mock_wiki):
        sr = SearchResult(
            text="**User**: hello\n**AI**: world",
            path="sources/2026-05-10.md",
            start_line=1, end_line=2,
            score=0.88, source="wiki",
        )
        mock_wiki.search.return_value = [sr]

        turns = query_obj.search_turns("query", "sess-1", max_results=3)
        assert len(turns) == 1
        turn = turns[0]
        assert turn.user_input == "hello"
        assert turn.agent_response == "world"
        assert turn.session_id == "sess-1"
        assert turn.metadata["path"] == "sources/2026-05-10.md"
        assert turn.metadata["score"] == 0.88
        assert turn.metadata["source"] == "wiki"
        assert turn.importance == 0.88

    def test_search_turns_uses_wiki_prefix_for_turn_id(self, query_obj, mock_wiki):
        sr = SearchResult(
            text="**User**: hi\n**AI**: hi back",
            path="entities/x.md",
            start_line=5, end_line=6,
            score=0.5, source="wiki",
        )
        mock_wiki.search.return_value = [sr]
        turns = query_obj.search_turns("query", "sess-1")
        assert turns[0].turn_id == "wiki_entities/x.md_5"

    def test_search_turns_empty_when_no_results(self, query_obj, mock_wiki):
        mock_wiki.search.return_value = []
        turns = query_obj.search_turns("nothing", "sess-1")
        assert turns == []


class TestExtractHelpers:
    """Static text extraction methods."""

    def test_extract_user_from_bold_format(self):
        text = "**User**: hello world"
        result = WikiQuery._extract_user(text)
        assert result == "hello world"

    def test_extract_user_from_multiline(self):
        text = "some prefix\n**User**: the user message\n**AI**: the reply"
        result = WikiQuery._extract_user(text)
        assert result == "the user message"

    def test_extract_user_empty_when_not_found(self):
        result = WikiQuery._extract_user("no user here")
        assert result == ""

    def test_extract_agent_from_bold_format(self):
        text = "**AI**: agent reply here"
        result = WikiQuery._extract_agent(text)
        assert result == "agent reply here"

    def test_extract_agent_from_multiline(self):
        text = "**User**: hello\n**AI**: world\nmore stuff"
        result = WikiQuery._extract_agent(text)
        assert result == "world"

    def test_extract_agent_empty_when_not_found(self):
        result = WikiQuery._extract_agent("no agent here")
        assert result == ""
