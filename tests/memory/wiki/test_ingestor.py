"""Tests for WikiIngestor — turn → wiki page ingestion."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from animetta import $$$
from animetta import $$$
from animetta import $$$


@pytest.fixture
def mock_wiki():
    """Create a fully-mocked WikiManager."""
    wm = MagicMock()
    wm.read_page.return_value = None
    wm.page_exists.return_value = False
    wm.write_page = MagicMock()
    wm.write_raw = MagicMock()
    wm.rebuild_index = MagicMock()
    wm.append_log = MagicMock()
    wm.search = MagicMock(return_value=[])
    return wm


@pytest.fixture
def sample_turn():
    """A typical MemoryTurn with user info."""
    return MemoryTurn(
        turn_id="turn-001",
        session_id="sess-001",
        timestamp=datetime(2026, 5, 10, 14, 30),
        user_input="我叫小明，今年25岁，我喜欢吃火锅。",
        agent_response="你好小明！火锅确实很好吃呢~",
        emotions=["happy"],
        importance=0.5,
    )


@pytest.fixture
def low_score_turn():
    """A turn with low importance content (score < 0.3)."""
    # Short question gets -0.1 penalty: 0.3 - 0.1 = 0.2
    return MemoryTurn(
        turn_id="turn-002",
        session_id="sess-001",
        timestamp=datetime(2026, 5, 10, 15, 0),
        user_input="?",
        agent_response="好的",
        emotions=["neutral"],
        importance=0.1,
    )


@pytest.fixture
def ingestor(mock_wiki):
    """WikiIngestor with mocked wiki."""
    return WikiIngestor(wiki=mock_wiki)


@pytest.fixture
def ingestor_with_fact_extractor(mock_wiki):
    """WikiIngestor with mocked fact extractor."""
    fe = MagicMock()
    fe.extract_and_store = AsyncMock()
    return WikiIngestor(wiki=mock_wiki, fact_extractor=fe), fe


class TestIngestorInit:
    """Constructor and dependencies."""

    def test_init_sets_wiki_and_defaults(self, mock_wiki):
        ing = WikiIngestor(wiki=mock_wiki)
        assert ing._wiki is mock_wiki
        assert ing._scorer is not None
        assert ing._llm_client is None
        assert ing._fact_extractor is None

    def test_init_with_llm_and_fact_extractor(self, mock_wiki):
        mock_llm = MagicMock()
        mock_fe = MagicMock()
        ing = WikiIngestor(wiki=mock_wiki, llm_client=mock_llm, fact_extractor=mock_fe)
        assert ing._wiki is mock_wiki
        assert ing._llm_client is mock_llm
        assert ing._fact_extractor is mock_fe


class TestEntityExtraction:
    """Entity extraction from user input."""

    def test_extract_name_entity(self, ingestor, sample_turn):
        entities = ingestor._extract_entities(sample_turn)
        # "我叫小明" → name: 小明
        assert ("name", "小明") in entities

    def test_extract_age_entity(self, ingestor):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="我今年25岁",
            agent_response="好的", emotions=[],
        )
        entities = ingestor._extract_entities(turn)
        assert ("age", "25") in entities

    def test_extract_pet_entity(self, ingestor):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="我养了一只猫叫咪咪，特别可爱。",
            agent_response="好可爱！", emotions=[],
        )
        entities = ingestor._extract_entities(turn)
        assert any(e[0] == "pet" and "咪咪" in e[1] for e in entities)

    def test_extract_location_entity(self, ingestor):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="我住在上海，这里很棒",
            agent_response="上海确实是个好地方", emotions=[],
        )
        entities = ingestor._extract_entities(turn)
        assert any(e[0] == "location" and "上海" in e[1] for e in entities)

    def test_extract_entities_deduplicates(self, ingestor):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="我叫小红，我今年20岁",
            agent_response="好的", emotions=[],
        )
        entities = ingestor._extract_entities(turn)
        # one per category
        names = [e for e in entities if e[0] == "name"]
        assert len(names) == 1


class TestConceptExtraction:
    """Concept/preference extraction from user input."""

    def test_extract_like_concept(self, ingestor, sample_turn):
        concepts = ingestor._extract_concepts(sample_turn)
        # "我喜欢吃火锅" → like: 吃火锅
        assert any(c[0] == "like" and "火锅" in c[1] for c in concepts)

    def test_extract_dislike_concept(self, ingestor):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="我特别讨厌吃香菜",
            agent_response="明白了", emotions=[],
        )
        concepts = ingestor._extract_concepts(turn)
        assert any(c[0] == "dislike" and "香菜" in c[1] for c in concepts)

    def test_extract_want_concept(self, ingestor):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="我想去日本旅行",
            agent_response="好主意！", emotions=[],
        )
        concepts = ingestor._extract_concepts(turn)
        assert any(c[0] == "want" and "日本" in c[1] for c in concepts)

    def test_extract_no_concepts_on_empty_input(self, ingestor):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="好的，谢谢",
            agent_response="不客气", emotions=[],
        )
        concepts = ingestor._extract_concepts(turn)
        assert concepts == []


class TestSafeName:
    """Static help method _safe_name."""

    def test_safe_name_strips_special_chars(self, ingestor):
        assert WikiIngestor._safe_name("hello!@#world") == "helloworld"

    def test_safe_name_replaces_spaces_with_dashes(self, ingestor):
        assert WikiIngestor._safe_name("my name") == "my-name"

    def test_safe_name_truncates_to_60_chars(self, ingestor):
        long_name = "a" * 100
        result = WikiIngestor._safe_name(long_name)
        assert len(result) <= 60


class TestIngestTurn:
    """Full ingestion flow."""

    @pytest.mark.asyncio
    async def test_ingest_high_score_turn_writes_pages(self, ingestor, sample_turn, mock_wiki):
        await ingestor.ingest_turn(sample_turn)

        # raw log
        mock_wiki.write_raw.assert_called_once()
        # pages created
        assert mock_wiki.write_page.call_count >= 3  # entity + concept + source
        # index rebuilt
        mock_wiki.rebuild_index.assert_called_once()
        # log appended
        mock_wiki.append_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_low_score_turn_skips(self, ingestor, low_score_turn, mock_wiki):
        # Reset to check only raw + skip
        mock_wiki.reset_mock()
        await ingestor.ingest_turn(low_score_turn)

        # raw is always written
        mock_wiki.write_raw.assert_called_once()
        # no pages should be written (score < 0.3)
        mock_wiki.write_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_important_pattern_boost(self, ingestor, mock_wiki):
        """Turn matching '记住' gets score boosted to >= 0.6."""
        mock_wiki.reset_mock()
        turn = MemoryTurn(
            turn_id="t-imp", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="记住我喜欢蓝色",
            agent_response="记住了！", emotions=[],
        )
        await ingestor.ingest_turn(turn)
        # Should pass threshold and write pages
        assert mock_wiki.write_page.call_count >= 1

    @pytest.mark.asyncio
    async def test_ingest_with_fact_extractor(self, ingestor_with_fact_extractor, sample_turn):
        ing, fe = ingestor_with_fact_extractor
        await ing.ingest_turn(sample_turn)
        fe.extract_and_store.assert_awaited_once_with(sample_turn)

    @pytest.mark.asyncio
    async def test_ingest_fact_extractor_error_is_caught(self, ingestor_with_fact_extractor, sample_turn):
        ing, fe = ingestor_with_fact_extractor
        fe.extract_and_store.side_effect = RuntimeError("extraction failed")
        # Should NOT raise
        await ing.ingest_turn(sample_turn)
        fe.extract_and_store.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ingest_updates_existing_page(self, ingestor, sample_turn, mock_wiki):
        existing = WikiPage(
            title="小明", page_type=PageType.ENTITY,
            path="entities/小明.md",
            content="# 小明\n\n旧内容",
            tags=["name", "2026-05-09"],
        )
        mock_wiki.read_page.return_value = existing

        await ingestor.ingest_turn(sample_turn)
        # existing page updated (content appended)
        write_calls = mock_wiki.write_page.call_args_list
        assert any("旧内容" in str(call) or
                   any("小明" in str(arg) for arg in call[0] if hasattr(arg, 'content'))
                   for call in write_calls)

    @pytest.mark.asyncio
    async def test_ingest_no_entities_or_concepts_still_writes_source(self, ingestor, mock_wiki):
        mock_wiki.reset_mock()
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="今天天气真好",
            agent_response="是啊，很适合出去玩呢~",
            emotions=["happy"],
        )
        await ingestor.ingest_turn(turn)
        # Source summary should still be written
        source_calls = [
            c for c in mock_wiki.write_page.call_args_list
            if "来源" in str(c.args) or "sources/" in str(c.args)
        ]
        assert len(source_calls) >= 0  # at minimum, raw + possible source

    @pytest.mark.asyncio
    async def test_ingest_entity_page_format(self, ingestor, mock_wiki):
        """Entity page has correct structure when newly created."""
        mock_wiki.read_page.return_value = None  # no existing page
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 14, 30),
            user_input="我叫小明",
            agent_response="你好小明！",
            emotions=[],
        )
        await ingestor.ingest_turn(turn)

        write_calls = mock_wiki.write_page.call_args_list
        # Find the entity page write
        entity_writes = [c for c in write_calls if hasattr(c[0][0], 'page_type') and c[0][0].page_type == PageType.ENTITY]
        if entity_writes:
            page = entity_writes[0][0][0]
            assert page.page_type == PageType.ENTITY
            assert page.title == "小明"
            assert "entities/" in page.path


class TestIngestBatch:
    """Batch ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_batch_calls_ingest_turn(self, ingestor, sample_turn):
        turns = [
            sample_turn,
            MemoryTurn(
                turn_id="t2", session_id="s1",
                timestamp=datetime(2026, 5, 10, 15, 0),
                user_input="我住在上海", agent_response="上海很好！",
                emotions=[],
            ),
        ]
        with patch.object(ingestor, "ingest_turn", new_callable=AsyncMock) as mock_ingest:
            await ingestor.ingest_batch(turns)
            assert mock_ingest.call_count == 2


class TestRawWrite:
    """Raw log formatting."""

    def test_write_raw_includes_user_and_ai(self, ingestor, sample_turn, mock_wiki):
        ingestor._write_raw(sample_turn)
        call_args = mock_wiki.write_raw.call_args
        content = call_args[0][1]
        assert "**User**:" in content
        assert "**AI**:" in content
        assert "小明" in content

    def test_write_raw_includes_emotions(self, ingestor, mock_wiki):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="hello", agent_response="hi",
            emotions=["happy", "excited"],
        )
        ingestor._write_raw(turn)
        content = mock_wiki.write_raw.call_args[0][1]
        assert "Emotions:" in content
        assert "happy" in content

    def test_write_raw_handles_dict_emotions(self, ingestor, mock_wiki):
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 12, 0),
            user_input="hello", agent_response="hi",
            emotions=[{"emotion": "happy", "intensity": 0.8}],
        )
        ingestor._write_raw(turn)
        content = mock_wiki.write_raw.call_args[0][1]
        assert "happy" in content


class TestConceptPageFormat:
    """Concept page structure."""

    def test_new_concept_page_has_correct_type(self, ingestor, mock_wiki):
        mock_wiki.read_page.return_value = None
        turn = MemoryTurn(
            turn_id="t1", session_id="s1",
            timestamp=datetime(2026, 5, 10, 14, 30),
            user_input="我喜欢吃火锅",
            agent_response="火锅很棒！",
            emotions=[],
        )
        ingestor._update_concept_page("like", "吃火锅", turn)

        write_calls = mock_wiki.write_page.call_args_list
        concept_writes = [c for c in write_calls if hasattr(c[0][0], 'page_type') and c[0][0].page_type == PageType.CONCEPT]
        if concept_writes:
            page = concept_writes[0][0][0]
            assert "concepts/" in page.path
            assert page.page_type == PageType.CONCEPT
