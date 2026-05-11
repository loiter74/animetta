"""Integration tests: full memory pipeline with mocked LLM."""

import os, sys, uuid, json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Any

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.anima.memory.models.memory_entry import MemoryEntry
from src.anima.memory.models.turns import MemoryTurn
from src.anima.memory.storage.memory_entry_store import MemoryEntryStore
from src.anima.memory.fact_extractor import FactExtractor, ExtractedFact
from src.anima.memory.search.scorer import MemoryScorer, DECAY_ARCHIVE_THRESHOLD
from src.anima.memory.learner.fact_extractor import format_facts_for_wiki
from src.anima.memory.learner.persona_optimizer import (
    format_suggestions_yaml,
    _summarize_persona,
    _clean_json,
)

# ── Mock LLM ───────────────────────────────────────────────


@dataclass
class MockLLMResponse:
    content: str

    def get(self, key: str, default: Any = "") -> Any:
        return getattr(self, key, default)


class MockLLMClient:
    """Returns predefined JSON responses for different prompt patterns."""

    def __init__(self, responses: dict[str, dict] | None = None):
        self._responses = responses or {}
        self.last_messages: list = []

    async def chat(self, messages: list, **kwargs) -> dict:
        self.last_messages = messages
        system = ""
        user = ""
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                user = m["content"]

        # Match against registered patterns
        for pattern, response in self._responses.items():
            if pattern in system or pattern in user:
                return {"content": json.dumps(response, ensure_ascii=False)}

        # Default: return facts about a Python-loving user
        return {"content": json.dumps([
            {"fact": "User likes Python", "category": "preference", "confidence": 0.9, "is_static": True},
            {"fact": "User lives in Beijing", "category": "identity", "confidence": 0.85, "is_static": True},
        ], ensure_ascii=False)}


# ── Default mock response ──────────────────────────────────

DEFAULT_FACTS = [
    {"fact": "User likes Python", "category": "preference", "confidence": 0.9, "is_static": True},
    {"fact": "User lives in Beijing", "category": "identity", "confidence": 0.85, "is_static": True},
]

DEFAULT_PATTERNS = {
    "patterns": [
        {"pattern": "User frequently asks about Python", "category": "interest", "confidence": 0.8, "evidence": ["t1", "t2"]},
    ]
}

DEFAULT_PERSONA_ANALYSIS = {
    "strengths": [{"pattern": "Good at explaining code", "evidence": "3 sessions", "confidence": 0.9}],
    "weaknesses": [{"pattern": "Sometimes too terse", "severity": "medium", "evidence": "2 sessions"}],
    "suggestions": [{
        "target_field": "personality.traits",
        "action": "add",
        "current_value": "",
        "suggested_value": "Be more patient with new users",
        "rationale": "Users frequently ask for clarification in 3+ sessions",
        "confidence": 0.8,
    }],
    "summary": "Overall persona is working well, minor tone adjustments suggested",
}

# ── Fixtures ───────────────────────────────────────────────


@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest.fixture
def entry_store():
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(MemoryEntryStore.ddl())
    s = MemoryEntryStore(conn)
    yield s
    conn.close()


def _make_turn(user_text: str, ai_text: str = "OK", emotions: list[str] | None = None) -> MemoryTurn:
    return MemoryTurn(
        turn_id=str(uuid.uuid4()),
        session_id="test-session",
        timestamp=datetime.now(timezone.utc),
        user_input=user_text,
        agent_response=ai_text,
        emotions=emotions or [],
    )


# ── Scenario 1: Extract → Store → Search ───────────────────

class TestExtractStoreSearch:
    """Full pipeline: LLM extract facts → store → search retrieval."""

    async def test_extract_and_search(self, mock_llm, entry_store):
        extractor = FactExtractor(entry_store=entry_store, llm_client=mock_llm)
        turn = _make_turn("I like Python and live in Beijing")

        entries = await extractor.extract_and_store(turn, space_id="test-space")
        assert len(entries) == 2, f"Expected 2 facts, got {len(entries)}"

        results = entry_store.search_by_space("test-space", limit=10)
        memories = [r.memory for r in results]
        assert "User likes Python" in memories
        assert "User lives in Beijing" in memories

    async def test_dedup_skips_duplicate(self, mock_llm, entry_store):
        extractor = FactExtractor(entry_store=entry_store, llm_client=mock_llm)
        turn = _make_turn("I like Python")

        first = await extractor.extract_and_store(turn, space_id="test")
        second = await extractor.extract_and_store(turn, space_id="test")

        assert len(first) > 0
        # Same input should not create new entries (fact unchanged → skip)
        results = entry_store.search_by_space("test")
        memories = [r.memory for r in results]
        # "User likes Python" should appear only once
        assert memories.count("User likes Python") == 1


# ── Scenario 2: Emotion → Decay → Archive ──────────────────

class TestEmotionDecayArchive:
    """Emotion-tagged entries decay slower and resist archival."""

    def test_archive_decayed_removes_low_value(self, entry_store):
        now = datetime.now(timezone.utc)
        old_iso = (now - timedelta(days=400)).isoformat()

        low = MemoryEntry(
            id=str(uuid.uuid4()), memory="old trivial fact", space_id="test",
            version=1, is_latest=True, confidence=0.3,
            emotion_value=None, retrieval_count=0,
            created_at=old_iso, updated_at=old_iso,
        )
        high = MemoryEntry(
            id=str(uuid.uuid4()), memory="important emotional fact", space_id="test",
            version=1, is_latest=True, confidence=0.9,
            emotion_value=0.9, retrieval_count=5,
            created_at=now.isoformat(), updated_at=now.isoformat(),
        )
        entry_store.create(low)
        entry_store.create(high)
        # create() overrides created_at with now — backdate the low entry
        entry_store.conn.execute(
            "UPDATE memory_entries SET created_at = ?, updated_at = ? WHERE id = ?",
            (old_iso, old_iso, low.id),
        )
        entry_store.conn.commit()

        archived = entry_store.archive_decayed(threshold=DECAY_ARCHIVE_THRESHOLD)

        # Low should be archived, high should survive
        low_fetched = entry_store.get(low.id)
        high_fetched = entry_store.get(high.id)
        assert low_fetched.is_archived, "Low-value old entry should be archived"
        assert not high_fetched.is_archived, "High-value entry should survive"


# ── Scenario 3: Emotion-Weighted Search Ranking ─────────────

class TestEmotionWeightedSearch:
    """Emotion-tagged memories rank higher in search results."""

    def test_emotion_boost_preserves_ranking(self, entry_store):
        now_iso = datetime.now(timezone.utc).isoformat()

        neutral = MemoryEntry(
            id=str(uuid.uuid4()), memory="User likes coffee", space_id="test",
            version=1, is_latest=True, confidence=0.7,
            emotion_value=None, retrieval_count=0,
            created_at=now_iso, updated_at=now_iso,
        )
        emotional = MemoryEntry(
            id=str(uuid.uuid4()), memory="User loves coffee passionately", space_id="test",
            version=1, is_latest=True, confidence=0.7,
            emotion_value=0.9, retrieval_count=0,
            created_at=now_iso, updated_at=now_iso,
        )
        entry_store.create(neutral)
        entry_store.create(emotional)

        neutral_score, _, _ = MemoryScorer.memory_score(
            confidence=0.7, created_at=now_iso, emotion_value=None,
        )
        emotional_score, _, _ = MemoryScorer.memory_score(
            confidence=0.7, created_at=now_iso, emotion_value=0.9,
        )
        assert emotional_score > neutral_score, \
            f"Emotional score ({emotional_score:.3f}) should exceed neutral ({neutral_score:.3f})"


# ── Scenario 4: Facts → Wiki Markdown ───────────────────────

class TestFactsToWiki:
    """Extracted facts are formatted into readable Wiki Markdown."""

    def test_categories_in_output(self):
        facts = [
            {"id": "1", "fact": "Likes Python", "category": "preference", "confidence": 0.9,
             "is_static": True, "source": "auto", "source_turn_id": "t1",
             "source_timestamp": datetime.now(timezone.utc).isoformat()},
            {"id": "2", "fact": "Lives in Beijing", "category": "identity", "confidence": 0.85,
             "is_static": True, "source": "auto", "source_turn_id": "t1",
             "source_timestamp": datetime.now(timezone.utc).isoformat()},
        ]
        result = format_facts_for_wiki(facts, "test-session")
        assert "Likes Python" in result
        assert "Lives in Beijing" in result
        assert "test-session" in result
        assert "提取数量" in result

    def test_empty_facts_returns_empty(self):
        assert format_facts_for_wiki([], "s") == ""


# ── Scenario 5: Persona Analysis Pipeline ──────────────────

class TestPersonaPipeline:
    """Persona analysis → suggestions YAML, end-to-end."""

    def test_pipeline_outputs_reviewable_yaml(self):
        result = format_suggestions_yaml(DEFAULT_PERSONA_ANALYSIS, "TestBot")
        assert "# Persona Evolution Suggestions" in result
        assert "TestBot" in result
        assert "applied: false" in result
        assert "Be more patient" in result
        assert "Auto-apply: false" in result

    def test_suggestions_without_changes(self):
        analysis = {"suggestions": [], "summary": "No changes needed"}
        result = format_suggestions_yaml(analysis, "Bot")
        assert "No changes needed" in result

    def test_persona_summary_includes_traits(self):
        config = {
            "name": "TestBot",
            "identity": "A helpful assistant.",
            "personality": {"traits": ["helpful", "concise"], "speaking_style": ["short sentences"]},
        }
        summary = _summarize_persona(config)
        assert "TestBot" in summary
        assert "helpful" in summary

    def test_clean_json_handles_all_formats(self):
        assert _clean_json("```json\n{}\n```") == "{}"
        assert _clean_json('{"a":1}') == '{"a":1}'
        assert _clean_json("  ```\n[]\n```  ") == "[]"
