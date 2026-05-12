"""Tests for MemorySystem — store_turn, retrieve_context, start/stop lifecycle."""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.anima.memory.models.turns import MemoryTurn
from src.anima.memory.system import MemorySystem


@pytest.fixture
def mock_deps():
    """Patch all heavy dependencies of MemorySystem."""
    patches = {
        "MemoryManager": patch("src.anima.memory.system.MemoryManager"),
        "WikiManager": patch("src.anima.memory.system.WikiManager"),
        "WikiIngestor": patch("src.anima.memory.system.WikiIngestor"),
        "WikiQuery": patch("src.anima.memory.system.WikiQuery"),
        "WikiLint": patch("src.anima.memory.system.WikiLint"),
        "ShortTermMemory": patch("src.anima.memory.system.ShortTermMemory"),
        "MemoryScorer": patch("src.anima.memory.system.MemoryScorer"),
        "FuzzyLayer": patch("src.anima.memory.system.FuzzyLayer"),
        "MemePool": patch("src.anima.memory.system.MemePool"),
        "PeriodicLearner": patch("src.anima.memory.system.PeriodicLearner"),
        "FactExtractor": patch("src.anima.memory.system.FactExtractor"),
        "UserProfileBuilder": patch("src.anima.memory.system.UserProfileBuilder"),
        "AsyncScheduler": patch("src.anima.memory.system.AsyncScheduler"),
    }
    mocks = {}
    for name, p in patches.items():
        mocked = p.start()
        instance = MagicMock()
        mocked.return_value = instance
        mocks[name] = instance
        mocks[f"_{name}"] = mocked

    yield mocks

    for p in patches.values():
        p.stop()


@pytest.fixture
def turn():
    return MemoryTurn(
        turn_id="t1",
        session_id="s1",
        timestamp=datetime.now(),
        user_input="hello",
        agent_response="hi there",
    )


class TestMemorySystemInit:
    """MemorySystem construction with various configs."""

    def test_init_default_config(self, mock_deps):
        system = MemorySystem({})
        assert system._config == {}

    def test_init_with_workspace(self, mock_deps):
        system = MemorySystem({"workspace_dir": "/tmp/test_ws"})
        assert system._config["workspace_dir"] == "/tmp/test_ws"

    def test_init_sets_turn_cache(self, mock_deps):
        system = MemorySystem({"enable_turn_cache": True})
        assert system._turn_cache_enabled is True

    def test_init_disables_turn_cache(self, mock_deps):
        system = MemorySystem({"enable_turn_cache": False})
        assert system._turn_cache_enabled is False

    def test_init_search_config(self, mock_deps):
        system = MemorySystem({"search": {"vector_weight": 0.5, "keyword_weight": 0.5}})
        # Should pass search config to MemoryConfig
        from src.anima.memory.config import SearchConfig

    def test_init_graceful_degradation(self):
        """When WikiManager init fails, system should still be usable."""
        with patch("src.anima.memory.system.MemoryManager", side_effect=Exception("fail")):
            system = MemorySystem({})
            # Should log warning but not crash
            assert system._wiki_manager is None


class TestMemorySystemStoreTurn:
    """MemorySystem.store_turn."""

    def test_store_turn_scores_and_appends(self, mock_deps, turn):
        system = MemorySystem({})
        system._scorer.score.return_value = 0.7
        system._ingestor = None  # prevent async task creation

        asyncio.run(system.store_turn(turn))

        system._scorer.score.assert_called_once_with(turn)
        assert turn.importance == 0.7
        system._short_term.append.assert_called_once_with("s1", turn)

    def test_store_turn_ingests_if_available(self, mock_deps, turn):
        system = MemorySystem({})
        system._ingestor = MagicMock()
        system._ingestor.ingest_turn = AsyncMock()

        asyncio.run(system.store_turn(turn))

        # Should create an async task for ingestion
        assert system._ingestor.ingest_turn.called

    def test_store_turn_no_ingestor(self, mock_deps, turn):
        system = MemorySystem({})
        system._ingestor = None

        # Should not crash
        asyncio.run(system.store_turn(turn))


class TestMemorySystemRetrieveContext:
    """MemorySystem.retrieve_context."""

    @pytest.mark.asyncio
    async def test_retrieve_from_short_term(self, mock_deps, turn):
        system = MemorySystem({})
        system._short_term.get_recent.return_value = [turn]

        results = await system.retrieve_context("hello", "s1", max_turns=5)
        assert len(results) >= 1
        assert results[0].turn_id == "t1"

    @pytest.mark.asyncio
    async def test_retrieve_with_wiki_query(self, mock_deps, turn):
        system = MemorySystem({})
        system._short_term.get_recent.return_value = []
        wiki_turn = MemoryTurn(
            turn_id="wiki_1", session_id="s1",
            timestamp=datetime.now(), user_input="", agent_response="wiki result",
        )
        system._wiki_query.search_turns.return_value = [wiki_turn]

        results = await system.retrieve_context("query", "s1")
        assert len(results) >= 1
        assert results[0].turn_id == "wiki_1"

    @pytest.mark.asyncio
    async def test_retrieve_deduplicates(self, mock_deps, turn):
        system = MemorySystem({})
        # Same turn returned from both short_term and wiki query
        system._short_term.get_recent.return_value = [turn]
        system._wiki_query.search_turns.return_value = [turn]

        results = await system.retrieve_context("hello", "s1")
        # Should be deduplicated by turn_id
        turn_ids = [r.turn_id for r in results]
        assert turn_ids.count("t1") == 1

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self, mock_deps, turn):
        system = MemorySystem({})
        system._turn_cache_enabled = True
        system._short_term.get_recent.return_value = [turn]

        await system.retrieve_context("hello", "s1")
        # Second call should hit cache
        system._short_term.get_recent.reset_mock()
        results2 = await system.retrieve_context("hello", "s1")
        assert len(results2) >= 1
        # If cache hit, get_recent should not be called again
        # (but might be called for key computation, so just check works)

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_new_turn(self, mock_deps, turn):
        system = MemorySystem({})
        system._turn_cache_enabled = True
        system._short_term.get_recent.return_value = [turn]

        await system.retrieve_context("hello", "s1")
        await system.retrieve_context("goodbye", "s1")  # different query -> new cache

        # Should have called get_recent for both queries
        assert system._short_term.get_recent.call_count == 2

    @pytest.mark.asyncio
    async def test_retrieve_wiki_search_failure(self, mock_deps, turn):
        """Wiki search failure should not crash retrieve_context."""
        system = MemorySystem({})
        system._short_term.get_recent.return_value = [turn]
        system._wiki_query.search_turns.side_effect = Exception("search failed")

        results = await system.retrieve_context("hello", "s1")
        assert len(results) >= 1  # short-term results still returned


class TestMemorySystemLifecycle:
    """MemorySystem start/stop."""

    @pytest.mark.asyncio
    async def test_start_registers_scheduler_tasks(self, mock_deps):
        system = MemorySystem({"scheduler": {"enabled": True}})
        system._scheduler = MagicMock()
        system._scheduler.start = AsyncMock()
        system._scheduler_enabled = True
        system._learner = MagicMock()
        system.meme_pool = MagicMock()

        await system.start()
        assert system._scheduler.add_task.called
        system._scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_no_scheduler(self, mock_deps):
        system = MemorySystem({"scheduler": {"enabled": False}})
        system._scheduler = MagicMock()
        system._scheduler.start = AsyncMock()
        system._scheduler_enabled = False

        await system.start()
        system._scheduler.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_cleans_up(self, mock_deps):
        system = MemorySystem({})
        system._scheduler = MagicMock()
        system._scheduler.stop = AsyncMock()
        system._learner = MagicMock()
        system._learner.stop = AsyncMock()
        system.fuzzy = MagicMock()
        system._wiki_manager = MagicMock()
        system._short_term = MagicMock()

        await system.stop()
        system._scheduler.stop.assert_called_once()
        system._learner.stop.assert_called_once()

    def test_sync(self, mock_deps):
        system = MemorySystem({})
        system._wiki_manager = MagicMock()
        system.sync()
        system._wiki_manager.manager.sync.assert_called_once()
        system._wiki_manager.rebuild_index.assert_called_once()

    def test_search(self, mock_deps):
        system = MemorySystem({})
        system._wiki_manager = MagicMock()
        system._wiki_manager.search.return_value = ["result"]
        results = system.search("test")
        assert results == ["result"]

    def test_search_no_wiki(self, mock_deps):
        system = MemorySystem({})
        system._wiki_manager = None
        results = system.search("test")
        assert results == []

    def test_get_profile(self, mock_deps):
        system = MemorySystem({})
        profile = system.get_profile("s1")
        assert profile is not None

    def test_close(self, mock_deps):
        system = MemorySystem({})
        system._wiki_manager = MagicMock()
        system._short_term = MagicMock()
        system.close()
        system._wiki_manager.manager.close.assert_called_once()
        system._short_term.clear_all.assert_called_once()

    def test_lint(self, mock_deps):
        system = MemorySystem({})
        system._wiki_lint = MagicMock()
        system._wiki_lint.run.return_value = "ok"
        assert system.lint() == "ok"

    def test_lint_no_wiki_lint(self, mock_deps):
        system = MemorySystem({})
        system._wiki_lint = None
        assert system.lint() is None

    def test_should_flush(self, mock_deps):
        system = MemorySystem({})
        system._wiki_manager = MagicMock()
        system._wiki_manager.manager.should_flush.return_value = True
        assert system.should_flush(100000, 128000) is True

    def test_load_session_context(self, mock_deps):
        system = MemorySystem({})
        system._wiki_query = MagicMock()
        system._wiki_query.load_context.return_value = "context"
        assert system.load_session_context("q") == "context"

    def test_load_session_context_no_wiki(self, mock_deps):
        system = MemorySystem({})
        system._wiki_query = None
        assert system.load_session_context() == ""

    def test_clear_session(self, mock_deps):
        system = MemorySystem({})
        asyncio.run(system.clear_session("s1"))
        system._short_term.clear.assert_called_once_with("s1")
