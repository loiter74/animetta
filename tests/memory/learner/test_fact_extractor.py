"""Tests for fact extraction adapter — extract_facts_batch and format_facts_for_wiki."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from animetta import $$$
from animetta import $$$


def _make_turn(
    turn_id: str = "t1",
    session_id: str = "s1",
    user_input: str = "Hello",
    agent_response: str = "Hi there",
) -> MemoryTurn:
    return MemoryTurn(
        turn_id=turn_id,
        session_id=session_id,
        timestamp=datetime(2026, 5, 10, 14, 0),
        user_input=user_input,
        agent_response=agent_response,
    )


def _make_fact_entry(
    entry_id: str = "e1",
    memory: str = "User likes cats",
    confidence: float = 0.9,
    category: str = "preference",
    is_static: bool = True,
) -> MagicMock:
    entry = MagicMock()
    entry.id = entry_id
    entry.memory = memory
    entry.confidence = confidence
    entry.category = category
    entry.is_static = is_static
    return entry


@pytest.fixture
def fact_extractor():
    fe = MagicMock()
    fe.extract_and_store = AsyncMock()
    return fe


class TestExtractFactsBatch:
    """extract_facts_batch function."""

    @pytest.mark.asyncio
    async def test_extracts_facts_above_threshold(self, fact_extractor):
        turn = _make_turn("t1")
        entry = _make_fact_entry("e1", "User likes cats", confidence=0.9)
        fact_extractor.extract_and_store.return_value = [entry]

        facts = await extract_facts_batch(fact_extractor, [turn], "s1")
        assert len(facts) == 1
        assert facts[0]["fact"] == "User likes cats"
        assert facts[0]["confidence"] == 0.9
        assert facts[0]["category"] == "preference"
        assert facts[0]["is_static"] is True
        assert facts[0]["source"] == "auto-extraction"
        assert facts[0]["source_turn_id"] == "t1"

    @pytest.mark.asyncio
    async def test_filters_below_threshold(self, fact_extractor):
        turn = _make_turn("t1")
        entry = _make_fact_entry("e1", "Low confidence fact", confidence=0.5)
        fact_extractor.extract_and_store.return_value = [entry]

        facts = await extract_facts_batch(fact_extractor, [turn], "s1", confidence_threshold=0.7)
        assert len(facts) == 0

    @pytest.mark.asyncio
    async def test_custom_confidence_threshold(self, fact_extractor):
        turn = _make_turn("t1")
        entry = _make_fact_entry("e1", "Mid confidence", confidence=0.6)
        fact_extractor.extract_and_store.return_value = [entry]

        facts = await extract_facts_batch(fact_extractor, [turn], "s1", confidence_threshold=0.5)
        assert len(facts) == 1

    @pytest.mark.asyncio
    async def test_skips_empty_turns(self, fact_extractor):
        turn = _make_turn("t1", user_input="", agent_response="")
        facts = await extract_facts_batch(fact_extractor, [turn], "s1")
        assert len(facts) == 0
        fact_extractor.extract_and_store.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_turn_without_user_input(self, fact_extractor):
        turn = _make_turn("t1", user_input="", agent_response="Hi")
        facts = await extract_facts_batch(fact_extractor, [turn], "s1")
        assert len(facts) == 0

    @pytest.mark.asyncio
    async def test_skips_turn_without_agent_response(self, fact_extractor):
        turn = _make_turn("t1", user_input="Hi", agent_response="")
        facts = await extract_facts_batch(fact_extractor, [turn], "s1")
        assert len(facts) == 0

    @pytest.mark.asyncio
    async def test_handles_extraction_error(self, fact_extractor):
        turn = _make_turn("t1")
        fact_extractor.extract_and_store.side_effect = RuntimeError("extraction failed")

        facts = await extract_facts_batch(fact_extractor, [turn], "s1")
        assert len(facts) == 0  # error is caught, batch continues

    @pytest.mark.asyncio
    async def test_mixed_turns(self, fact_extractor):
        good_turn = _make_turn("t1", user_input="Hello", agent_response="Hi")
        empty_turn = _make_turn("t2", user_input="", agent_response="")
        entry = _make_fact_entry("e1", "Mixed result", confidence=0.9)
        fact_extractor.extract_and_store.return_value = [entry]

        facts = await extract_facts_batch(fact_extractor, [good_turn, empty_turn], "s1")
        assert len(facts) == 1  # only good turn processed

    @pytest.mark.asyncio
    async def test_empty_turns_list(self, fact_extractor):
        facts = await extract_facts_batch(fact_extractor, [], "s1")
        assert facts == []

    @pytest.mark.asyncio
    async def test_multiple_facts_from_one_turn(self, fact_extractor):
        turn = _make_turn("t1")
        e1 = _make_fact_entry("e1", "Fact 1", confidence=0.95)
        e2 = _make_fact_entry("e2", "Fact 2", confidence=0.85)
        fact_extractor.extract_and_store.return_value = [e1, e2]

        facts = await extract_facts_batch(fact_extractor, [turn], "s1")
        assert len(facts) == 2

    @pytest.mark.asyncio
    async def test_passes_space_id_to_extractor(self, fact_extractor):
        turn = _make_turn("t1")
        fact_extractor.extract_and_store.return_value = []

        await extract_facts_batch(fact_extractor, [turn], "my_session")
        fact_extractor.extract_and_store.assert_called_once_with(turn, space_id="my_session")


class TestFormatFactsForWiki:
    """format_facts_for_wiki function."""

    def test_formats_empty_facts(self):
        assert format_facts_for_wiki([], "s1") == ""

    def test_formats_single_fact(self):
        facts = [{
            "id": "e1",
            "fact": "User likes cats",
            "category": "preference",
            "confidence": 0.9,
            "is_static": True,
            "source": "auto-extraction",
        }]
        result = format_facts_for_wiki(facts, "s1")
        assert "自动提取事实" in result
        assert "**来源会话**: s1" in result
        assert "**提取数量**: 1" in result
        assert "User likes cats" in result
        assert "🎯 偏好" in result

    def test_formats_multiple_categories(self):
        facts = [
            {"id": "e1", "fact": "Likes cats", "category": "preference", "confidence": 0.9, "is_static": True, "source": "x"},
            {"id": "e2", "fact": "Is a student", "category": "identity", "confidence": 0.8, "is_static": True, "source": "x"},
        ]
        result = format_facts_for_wiki(facts, "s1")
        assert "🎯 偏好" in result
        assert "👤 身份" in result
        assert "Likes cats" in result
        assert "Is a student" in result

    def test_formats_unknown_category(self):
        facts = [{
            "id": "e1",
            "fact": "Something",
            "category": "weird_category",
            "confidence": 0.9,
            "is_static": True,
            "source": "x",
        }]
        result = format_facts_for_wiki(facts, "s1")
        assert "weird_category" in result

    def test_includes_confidence_bar(self):
        facts = [{
            "id": "e1",
            "fact": "Test",
            "category": "other",
            "confidence": 0.75,
            "is_static": True,
            "source": "x",
        }]
        result = format_facts_for_wiki(facts, "s1")
        assert "75%" in result

    def test_includes_extraction_footer(self):
        facts = [{
            "id": "e1",
            "fact": "Test",
            "category": "other",
            "confidence": 0.5,
            "is_static": True,
            "source": "x",
        }]
        result = format_facts_for_wiki(facts, "s1")
        assert "PeriodicLearner 自动提取" in result
