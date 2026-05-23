"""Tests for ConversationSummarizer — LLM + rule-based summarization, wiki writing."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from animetta import $$$
from animetta import $$$


def _make_turn(
    turn_id: str = "t1",
    session_id: str = "s1",
    user_input: str = "Hello",
    agent_response: str = "Hi there",
    emotions: list[str] | None = None,
) -> MemoryTurn:
    return MemoryTurn(
        turn_id=turn_id,
        session_id=session_id,
        timestamp=datetime(2026, 5, 10, 14, 0),
        user_input=user_input,
        agent_response=agent_response,
        emotions=emotions or [],
    )


class TestFormatTurns:
    """_format_turns helper function."""

    def test_formats_single_turn(self):
        turn = _make_turn("t1", "s1", "Hi", "Hello")
        result = _format_turns([turn])
        assert "[14:00]" in result
        assert "用户: Hi" in result
        assert "AI: Hello" in result

    def test_formats_with_emotions(self):
        turn = _make_turn("t1", "s1", "Hi", "Hello", emotions=["happy", "excited"])
        result = _format_turns([turn])
        assert "[happy, excited]" in result

    def test_formats_empty_list(self):
        assert _format_turns([]) == ""


class TestCountMessages:
    """_count_messages helper function."""

    def test_counts_all(self):
        turns = [
            _make_turn("t1", user_input="Hi", agent_response="Hello"),
            _make_turn("t2", user_input="How are you?", agent_response="Good"),
            _make_turn("t3", user_input="", agent_response="Reply"),
        ]
        stats = _count_messages(turns)
        assert stats["total"] == 3
        assert stats["user"] == 2
        assert stats["ai"] == 3

    def test_counts_empty(self):
        stats = _count_messages([])
        assert stats["total"] == 0
        assert stats["user"] == 0
        assert stats["ai"] == 0


class TestSummarizerGroupByDate:
    """Date grouping logic."""

    def test_groups_single_date(self):
        turn = _make_turn("t1", session_id="s1")
        result = ConversationSummarizer._group_by_date([turn])
        assert len(result) == 1
        assert "2026-05-10" in result

    def test_groups_multiple_dates(self):
        t1 = _make_turn("t1")
        t2 = _make_turn("t2")
        t2.timestamp = datetime(2026, 5, 11, 10, 0)
        result = ConversationSummarizer._group_by_date([t1, t2])
        assert len(result) == 2
        assert len(result["2026-05-10"]) == 1
        assert len(result["2026-05-11"]) == 1

    def test_groups_empty(self):
        assert ConversationSummarizer._group_by_date([]) == {}


class TestSummarizerRuleBased:
    """Rule-based summarization (no LLM client)."""

    @pytest.mark.asyncio
    async def test_summarize_with_rules(self):
        summarizer = ConversationSummarizer(llm_client=None)
        turns = [
            _make_turn("t1", user_input="I like cats", agent_response="Cats are great!"),
            _make_turn("t2", user_input="Tell me about dogs", agent_response="Dogs too!"),
        ]
        logs = await summarizer.summarize(turns, "s1")
        assert len(logs) == 1
        assert logs[0].summary_type == "conversation"
        assert "对话摘要" in logs[0].content
        assert "核心话题" in logs[0].content
        assert "对话统计" in logs[0].content

    @pytest.mark.asyncio
    async def test_summarize_rule_based_empty_turns(self):
        summarizer = ConversationSummarizer(llm_client=None)
        logs = await summarizer.summarize([], "s1")
        assert logs == []

    @pytest.mark.asyncio
    async def test_summarize_batch_with_rules(self):
        summarizer = ConversationSummarizer(llm_client=None)
        turns_s1 = [_make_turn("t1", "s1")]
        turns_s2 = [_make_turn("t2", "s2")]
        logs = await summarizer.summarize_batch({"s1": turns_s1, "s2": turns_s2})
        assert len(logs) == 2


class TestSummarizerLLM:
    """LLM-based summarization."""

    @pytest.mark.asyncio
    async def test_summarize_with_llm_chat(self):
        llm = MagicMock()
        llm.chat = AsyncMock(return_value={"content": "LLM generated summary"})
        summarizer = ConversationSummarizer(llm_client=llm)
        turns = [_make_turn("t1")]
        logs = await summarizer.summarize(turns, "s1")
        assert len(logs) == 1
        assert logs[0].summary_type == "conversation"

    @pytest.mark.asyncio
    async def test_summarize_with_llm_ainvoke(self):
        llm = MagicMock()
        del llm.chat
        response = MagicMock()
        response.content = "LLM ainvoke summary"
        llm.ainvoke = AsyncMock(return_value=response)
        summarizer = ConversationSummarizer(llm_client=llm)
        turns = [_make_turn("t1")]
        logs = await summarizer.summarize(turns, "s1")
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_llm_fallback_on_failure(self):
        llm = MagicMock()
        llm.chat = AsyncMock(side_effect=RuntimeError("LLM down"))
        summarizer = ConversationSummarizer(llm_client=llm)
        turns = [_make_turn("t1", user_input="test message here")]
        logs = await summarizer.summarize(turns, "s1")
        assert len(logs) == 1
        assert "对话统计" in logs[0].content  # fallback to rules

    @pytest.mark.asyncio
    async def test_llm_neither_chat_nor_ainvoke(self):
        llm = MagicMock(spec=[])
        summarizer = ConversationSummarizer(llm_client=llm)
        turns = [_make_turn("t1", user_input="test message here")]
        logs = await summarizer.summarize(turns, "s1")
        assert len(logs) == 1
        assert "对话统计" in logs[0].content

    @pytest.mark.asyncio
    async def test_llm_chat_str_response(self):
        llm = MagicMock()
        llm.chat = AsyncMock(return_value="plain string response")
        summarizer = ConversationSummarizer(llm_client=llm)
        turns = [_make_turn("t1")]
        logs = await summarizer.summarize(turns, "s1")
        assert len(logs) == 1
        assert logs[0].content == "plain string response"


class TestSummarizerWikiWriting:
    """Wiki source page writing."""

    def test_writes_new_wiki_source_file(self, tmp_path):
        summarizer = ConversationSummarizer(
            llm_client=None,
            config={"workspace_dir": str(tmp_path)},
        )
        summarizer._write_wiki_source("2026-05-10", "Test summary content")
        wiki_path = tmp_path / "wiki" / "sources" / "2026-05-10.md"
        assert wiki_path.exists()
        content = wiki_path.read_text(encoding="utf-8")
        assert "Test summary content" in content
        assert "type: source" in content

    def test_updates_existing_wiki_source(self, tmp_path):
        summarizer = ConversationSummarizer(
            llm_client=None,
            config={"workspace_dir": str(tmp_path)},
        )
        summarizer._write_wiki_source("2026-05-10", "First summary")
        summarizer._write_wiki_source("2026-05-10", "Updated summary")
        wiki_path = tmp_path / "wiki" / "sources" / "2026-05-10.md"
        content = wiki_path.read_text(encoding="utf-8")
        assert "Updated summary" in content

    def test_no_workspace_skips_writing(self):
        summarizer = ConversationSummarizer()
        summarizer._write_wiki_source("2026-05-10", "summary")
        # Should not raise

    def test_replace_or_append_abstract_replaces(self):
        existing = "## Intro\n\n## AI生成摘要\n\nOld summary\n\n---\n\nMore"
        new_abstract = "\n## AI生成摘要\n\nNew summary\n\n"
        result = ConversationSummarizer._replace_or_append_abstract(existing, new_abstract)
        assert "New summary" in result
        assert "Old summary" not in result

    def test_replace_or_append_abstract_appends(self):
        existing = "## Intro\n\nSome content"
        new_abstract = "\n## AI生成摘要\n\nNew summary\n\n"
        result = ConversationSummarizer._replace_or_append_abstract(existing, new_abstract)
        assert "New summary" in result
        assert "Some content" in result


class TestLearningLog:
    """LearningLog dataclass behavior."""

    def test_learninglog_defaults(self):
        log = LearningLog()
        assert log.id == ""
        assert log.session_id == ""
        assert log.summary_type == ""
        assert log.content == ""

    def test_learninglog_with_values(self):
        now = datetime.now()
        log = LearningLog(
            id="abc",
            session_id="s1",
            summary_type="conversation",
            content="test",
            source_ids='["t1"]',
            created_at=now,
        )
        assert log.id == "abc"
        assert log.session_id == "s1"
        assert log.created_at == now
