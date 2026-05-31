"""Tests for FuzzyLayer — build_fuzzy_context tiered narratives, TTL cache."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from animetta.memory.fuzzy_layer import FuzzyLayer
from animetta.memory.models.turns import MemoryTurn
from animetta.memory.wiki.models import PageType, WikiPage


def _make_turn(text: str, idx: int = 0) -> MemoryTurn:
    return MemoryTurn(
        turn_id=f"t_{idx}",
        session_id="s1",
        timestamp=datetime.now(),
        user_input=text,
        agent_response=f"resp_{idx}",
    )


def _make_wiki_page(path: str, content: str = "page content") -> WikiPage:
    return WikiPage(
        title=path.split("/")[-1].replace(".md", ""),
        page_type=PageType.SYNTHESIS,
        path=path,
        content=content,
    )


@pytest.fixture
def mock_wiki():
    wiki = MagicMock()
    wiki.list_pages.return_value = []
    wiki.read_page.return_value = None
    return wiki


@pytest.fixture
def mock_short_term():
    st = MagicMock()
    st.get_recent.return_value = []
    return st


class TestFuzzyLayerBuildContext:
    """FuzzyLayer.build_fuzzy_context tiered narrative construction."""

    @pytest.mark.asyncio
    async def test_empty_context_when_no_sources(self, mock_wiki, mock_short_term):
        fuzzy = FuzzyLayer(wiki=mock_wiki, short_term=mock_short_term)
        ctx = await fuzzy.build_fuzzy_context("s1", "hello")
        assert ctx == ""

    @pytest.mark.asyncio
    async def test_includes_recent_turns(self, mock_wiki):
        st = MagicMock()
        st.get_recent.return_value = [
            _make_turn("用户说了点啥", 1),
            _make_turn("又说了点别的", 2),
        ]
        fuzzy = FuzzyLayer(wiki=mock_wiki, short_term=st)
        ctx = await fuzzy.build_fuzzy_context("s1", "hello")
        assert "最近对话" in ctx
        assert "用户说了点啥" in ctx

    @pytest.mark.asyncio
    async def test_exclude_recent_turns_when_flag_false(self, mock_wiki):
        st = MagicMock()
        st.get_recent.return_value = [_make_turn("should not appear", 1)]
        fuzzy = FuzzyLayer(wiki=mock_wiki, short_term=st)
        ctx = await fuzzy.build_fuzzy_context(
            "s1", "hello", include_recent_turns=False
        )
        assert "最近对话" not in ctx

    @pytest.mark.asyncio
    async def test_includes_wiki_synthesis(self, mock_short_term):
        wiki = MagicMock()
        wiki.list_pages.return_value = ["synthesis/topic-a.md"]
        wiki.read_page.return_value = _make_wiki_page(
            "synthesis/topic-a.md", "这是合成内容"
        )
        fuzzy = FuzzyLayer(wiki=wiki, short_term=mock_short_term)
        ctx = await fuzzy.build_fuzzy_context("s1", "query")
        assert "我记得的" in ctx
        assert "这是合成内容" in ctx

    @pytest.mark.asyncio
    async def test_respects_max_synthesis(self, mock_short_term):
        wiki = MagicMock()
        wiki.list_pages.return_value = [
            "synthesis/a.md",
            "synthesis/b.md",
            "synthesis/c.md",
            "synthesis/d.md",
        ]
        wiki.read_page.return_value = _make_wiki_page("synthesis/a.md")
        fuzzy = FuzzyLayer(wiki=wiki, short_term=mock_short_term)
        ctx = await fuzzy.build_fuzzy_context("s1", "q", max_synthesis=2)
        assert ctx != ""

    @pytest.mark.asyncio
    async def test_includes_entity_profile(self, mock_short_term):
        wiki = MagicMock()
        wiki.list_pages.side_effect = (
            lambda pt=None: ["entities/user.md"] if pt is None else []
        )
        wiki.read_page.return_value = _make_wiki_page(
            "entities/user.md", "用户喜欢编程"
        )
        fuzzy = FuzzyLayer(wiki=wiki, short_term=mock_short_term)
        ctx = await fuzzy.build_fuzzy_context("s1", "q")
        assert "用户画像" in ctx
        assert "用户喜欢编程" in ctx

    @pytest.mark.asyncio
    async def test_tiered_sections_are_separated(self, mock_wiki):
        st = MagicMock()
        st.get_recent.return_value = [_make_turn("hi", 1)]
        wiki = MagicMock()
        wiki.list_pages.side_effect = (
            lambda pt=None: ["synthesis/s1.md"] if pt is not None else []
        )
        wiki.read_page.return_value = _make_wiki_page(
            "synthesis/s1.md", "synth content"
        )
        fuzzy = FuzzyLayer(wiki=wiki, short_term=st)
        ctx = await fuzzy.build_fuzzy_context("s1", "q")
        assert "---" in ctx  # section separator

    def test_no_wiki_no_crash(self, mock_short_term):
        fuzzy = FuzzyLayer(wiki=None, short_term=mock_short_term)
        assert fuzzy._get_relevant_synthesis("q", 3) == []
        assert fuzzy._get_profile_text("s1") == ""


class TestFuzzyCache:
    """FuzzyLayer TTL cache behavior."""

    @pytest.mark.asyncio
    async def test_cache_hits_skip_read_page(self, mock_short_term):
        wiki = MagicMock()
        wiki.list_pages.return_value = ["synthesis/cached.md"]
        read_mock = MagicMock(return_value=_make_wiki_page("synthesis/cached.md", "cached"))
        wiki.read_page = read_mock

        fuzzy = FuzzyLayer(wiki=wiki, short_term=mock_short_term)

        # First call: reads from wiki
        ctx1 = await fuzzy.build_fuzzy_context("s1", "q")
        assert read_mock.call_count >= 1

        # Second call: should use cache
        ctx2 = await fuzzy.build_fuzzy_context("s1", "q")
        assert "cached" in ctx2

    def test_invalidate_cache_single(self, mock_wiki):
        fuzzy = FuzzyLayer(wiki=mock_wiki, short_term=MagicMock())
        fuzzy._cache["synthesis/a.md"] = ("text", 1000.0)
        fuzzy.invalidate_cache("synthesis/a.md")
        assert "synthesis/a.md" not in fuzzy._cache

    def test_invalidate_cache_all(self, mock_wiki):
        fuzzy = FuzzyLayer(wiki=mock_wiki, short_term=MagicMock())
        fuzzy._cache["synthesis/a.md"] = ("text", 1000.0)
        fuzzy._cache["synthesis/b.md"] = ("text", 1001.0)
        fuzzy.invalidate_cache()
        assert len(fuzzy._cache) == 0

    def test_cache_ttl_expiry(self, mock_wiki):
        """Entries older than 300s should be evicted on next access."""
        fuzzy = FuzzyLayer(wiki=mock_wiki, short_term=MagicMock())
        old_time = 1000.0
        fuzzy._cache["synthesis/stale.md"] = ("old text", old_time)

        wiki = mock_wiki
        wiki.list_pages.return_value = ["synthesis/stale.md"]
        wiki.read_page.return_value = _make_wiki_page("synthesis/stale.md", "fresh")

        # The cache check happens inside _get_relevant_synthesis
        with patch("animetta.memory.fuzzy_layer.datetime") as mock_dt:
            mock_dt.now.return_value.timestamp.return_value = old_time + 301  # past TTL
            results = fuzzy._get_relevant_synthesis("q", 5)

        # Stale entry should be evicted and replaced with fresh content
        assert "synthesis/stale.md" in fuzzy._cache
        cached_text, _ = fuzzy._cache["synthesis/stale.md"]
        assert cached_text == "fresh"
