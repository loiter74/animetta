"""Tests for PeriodicLearner — scheduled tasks, lifecycle, DB operations."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest



def _make_turn(turn_id: str, session_id: str = "s1") -> MemoryTurn:
    return MemoryTurn(
        turn_id=turn_id,
        session_id=session_id,
        timestamp=datetime(2026, 5, 10, 14, 0),
        user_input="Hello",
        agent_response="Hi there",
        emotions=["neutral"],
    )


def _make_log(
    log_id: str = "log1",
    session_id: str = "s1",
    summary_type: str = "conversation",
    content: str = "summary content",
    source_ids: str = '["t1"]',
) -> LearningLog:
    return LearningLog(
        id=log_id,
        session_id=session_id,
        summary_type=summary_type,
        content=content,
        source_ids=source_ids,
        created_at=datetime.now(),
    )


@pytest.fixture
def memory_system():
    ms = MagicMock()
    st = MagicMock()
    st._cache = {}
    ms._short_term = st
    ms._wiki_manager = MagicMock()
    ms._wiki_manager.write_page = MagicMock()
    ms._wiki_manager.list_pages = MagicMock(return_value=[])
    ms._wiki_manager.read_page = MagicMock(return_value=None)
    return ms


@pytest.fixture
def engine(memory_system, tmp_path):
    with patch("anima.memory.learner.engine.ConversationSummarizer") as m_summ, \
         patch("anima.memory.learner.engine.PatternExtractor") as m_pat, \
         patch("anima.memory.learner.engine.MemeDiscoverer") as m_meme:
        m_summ.return_value = MagicMock()
        m_pat.return_value = MagicMock()
        m_meme.return_value = MagicMock()

        e = PeriodicLearner(
            memory_system=memory_system,
            llm_client=MagicMock(),
            config={"workspace_dir": str(tmp_path)},
        )
        yield e


class TestPeriodicLearnerInit:
    """Constructor and config reading."""

    def test_init_defaults(self, memory_system):
        e = PeriodicLearner(memory_system=memory_system, config={})
        assert e._memory_system is memory_system
        assert e._llm_client is None
        assert e._config == {}
        assert e._summarizer is not None
        assert e._pattern_extractor is not None
        assert e._meme_discoverer is not None

    def test_init_with_config(self, memory_system, tmp_path):
        config = {
            "workspace_dir": str(tmp_path),
            "fact_confidence_threshold": 0.8,
            "persona_auto_apply": True,
            "persona_min_logs": 5,
            "log_retention_days": 30,
            "patterns_per_run": 3,
            "meme_candidates_per_run": 2,
        }
        e = PeriodicLearner(memory_system=memory_system, config=config)
        assert e._fact_confidence_threshold == 0.8
        assert e._persona_auto_apply is True
        assert e._persona_min_logs == 5
        assert e._log_retention_days == 30

    def test_init_with_llm_client(self, memory_system):
        llm = MagicMock()
        e = PeriodicLearner(memory_system=memory_system, llm_client=llm, config={})
        assert e._llm_client is llm


class TestPeriodicLearnerLifecycle:
    """Start/stop lifecycle."""

    def test_start_ensures_db(self, engine):
        engine.start_sync = lambda: engine._ensure_db()
        engine.start_sync()
        assert engine._conn is not None
        assert engine._db_path is not None

    @pytest.mark.asyncio
    async def test_start_async(self, engine):
        await engine.start()
        assert engine._conn is not None

    @pytest.mark.asyncio
    async def test_stop_closes_connection(self, engine):
        engine._ensure_db()
        assert engine._conn is not None
        await engine.stop()
        assert engine._conn is None

    @pytest.mark.asyncio
    async def test_stop_no_connection(self, engine):
        await engine.stop()
        assert engine._conn is None


class TestConsolidateConversations:
    """consolidate_conversations scheduled task."""

    @pytest.mark.asyncio
    async def test_no_cache_returns_early(self, engine, memory_system):
        memory_system._short_term = MagicMock(spec=[])
        await engine.consolidate_conversations()

    @pytest.mark.asyncio
    async def test_no_sessions(self, engine, memory_system):
        memory_system._short_term._cache = {}
        await engine.consolidate_conversations()

    @pytest.mark.asyncio
    async def test_consolidates_sessions(self, engine, memory_system):
        t1 = _make_turn("t1", "s1")
        memory_system._short_term._cache = {"s1": [t1]}
        engine._summarizer.summarize_batch = AsyncMock(return_value=[])
        await engine.consolidate_conversations()
        engine._summarizer.summarize_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_stores_logs_on_success(self, engine, memory_system):
        t1 = _make_turn("t1", "s1")
        memory_system._short_term._cache = {"s1": [t1]}
        log = _make_log("log1", "s1")
        engine._summarizer.summarize_batch = AsyncMock(return_value=[log])
        engine._ensure_db()
        await engine.consolidate_conversations()
        stored = engine._get_recent_logs("conversation")
        assert len(stored) >= 1

    @pytest.mark.asyncio
    async def test_handles_exception(self, engine, memory_system):
        memory_system._short_term._cache = {"s1": [_make_turn("t1")]}
        engine._summarizer.summarize_batch = AsyncMock(side_effect=RuntimeError("boom"))
        engine._ensure_db()
        await engine.consolidate_conversations()  # should not raise


class TestExtractPatterns:
    """extract_patterns scheduled task."""

    @pytest.mark.asyncio
    async def test_no_recent_logs(self, engine):
        engine._ensure_db()
        await engine.extract_patterns()

    @pytest.mark.asyncio
    async def test_extracts_patterns(self, engine):
        log = _make_log("log1", "s1", "conversation", "content", '["t1"]')
        engine._ensure_db()
        engine._store_logs([log])
        engine._content_to_turns = MagicMock(return_value=[_make_turn("t1")])
        engine._pattern_extractor.extract_patterns = AsyncMock(return_value=[])
        engine._meme_discoverer.discover_candidates = AsyncMock(return_value=[])
        await engine.extract_patterns()
        engine._pattern_extractor.extract_patterns.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_exception(self, engine):
        engine._ensure_db()
        engine._conn = None  # force error path
        engine._pattern_extractor.extract_patterns = AsyncMock(side_effect=RuntimeError("boom"))
        await engine.extract_patterns()  # should not raise


class TestDbOperations:
    """SQLite storage operations."""

    def test_ensure_db_memory(self, engine):
        del engine._config["workspace_dir"]
        engine._ensure_db()
        assert engine._db_path == ":memory:"
        assert engine._conn is not None

    def test_store_and_get_logs(self, engine):
        engine._ensure_db()
        log = _make_log("abc", "s1", "conversation", "hello", '["t1"]')
        engine._store_logs([log])
        recent = engine._get_recent_logs("conversation")
        assert len(recent) == 1
        assert recent[0].id == "abc"
        assert recent[0].content == "hello"

    def test_get_recent_logs_empty(self, engine):
        engine._ensure_db()
        assert engine._get_recent_logs("conversation") == []

    def test_get_recent_logs_no_connection(self, engine):
        assert engine._get_recent_logs("conversation") == []

    def test_content_to_turns_handles_missing_fields(self, engine):
        """_content_to_turns catches TypeError from missing required MemoryTurn fields."""
        log = _make_log(source_ids='["tid1", "tid2"]')
        turns = engine._content_to_turns(log)
        assert turns == []

    def test_content_to_turns_empty(self, engine):
        log = _make_log(source_ids="[]")
        turns = engine._content_to_turns(log)
        assert turns == []

    def test_content_to_turns_none_source(self, engine):
        log = _make_log(source_ids="")
        turns = engine._content_to_turns(log)
        assert turns == []

    def test_row_to_learninglog(self, engine):
        engine._ensure_db()
        engine._conn.execute(
            "INSERT INTO learning_logs (id, session_id, summary_type, content, source_ids) VALUES (?, ?, ?, ?, ?)",
            ("r1", "s1", "conversation", "c", '[]'),
        )
        engine._conn.commit()
        row = engine._conn.execute("SELECT * FROM learning_logs WHERE id='r1'").fetchone()
        log = engine._row_to_learninglog(row)
        assert log.id == "r1"
        assert log.summary_type == "conversation"

    def test_upsert_processed_session(self, engine):
        engine._ensure_db()
        engine._upsert_processed_session("sess1")
        sessions = engine._load_processed_sessions()
        assert "sess1" in sessions

    def test_ensure_fact_extractor_unavailable(self, engine, memory_system):
        memory_system._ingestor = None
        engine._ensure_fact_extractor()
        assert engine._fact_extractor is None


class TestOptimizePersona:
    """Persona optimization task."""

    @pytest.mark.asyncio
    async def test_not_enough_logs(self, engine):
        engine._ensure_db()
        engine._persona_min_logs = 50
        await engine.optimize_persona()

    @pytest.mark.asyncio
    async def test_no_persona_config(self, engine, memory_system):
        engine._ensure_db()
        log = _make_log("l1", "s1", "conversation", "summary")
        engine._store_logs([log])
        engine._persona_min_logs = 1
        memory_system._config = {}
        await engine.optimize_persona()

    @pytest.mark.asyncio
    async def test_handles_exception(self, engine, memory_system):
        del engine._config["workspace_dir"]
        await engine.optimize_persona()  # should not raise
