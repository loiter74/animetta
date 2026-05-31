"""Tests for Meme, MemeSource, CognitiveAnalysis models."""

from __future__ import annotations

from datetime import datetime

import pytest

from animetta.memory.meme.models import CognitiveAnalysis, Meme, MemeSource


class TestMemeSource:
    """MemeSource enum values."""

    def test_values(self):
        assert MemeSource.AI.value == "ai"
        assert MemeSource.USER.value == "user"

    def test_all_values_covered(self):
        assert len(MemeSource) == 2


class TestCognitiveAnalysis:
    """CognitiveAnalysis dataclass."""

    def test_defaults(self):
        ca = CognitiveAnalysis()
        assert ca.humor_mechanism == ""
        assert ca.emotional_tone == ""
        assert ca.persona_fit_score == 0.5

    def test_custom_values(self):
        ca = CognitiveAnalysis(
            humor_mechanism="双关",
            context_trigger="当用户提到加班",
            emotional_tone="自嘲",
            persona_fit_score=0.8,
            usage_example="你今天又加班到几点?",
            roast="还行，可以更毒舌一点",
        )
        assert ca.humor_mechanism == "双关"
        assert ca.persona_fit_score == 0.8
        assert ca.roast == "还行，可以更毒舌一点"

    def test_to_dict(self):
        ca = CognitiveAnalysis(humor_mechanism="反讽", persona_fit_score=0.9)
        d = ca.to_dict()
        assert d["humor_mechanism"] == "反讽"
        assert d["persona_fit_score"] == 0.9

    def test_from_dict(self):
        data = {
            "humor_mechanism": "荒诞",
            "context_trigger": "讨论AI",
            "persona_fit_score": 0.7,
        }
        ca = CognitiveAnalysis.from_dict(data)
        assert ca is not None
        assert ca.humor_mechanism == "荒诞"
        assert ca.persona_fit_score == 0.7

    def test_from_dict_none(self):
        assert CognitiveAnalysis.from_dict(None) is None

    def test_from_dict_empty(self):
        ca = CognitiveAnalysis.from_dict({})
        assert ca is not None
        assert ca.humor_mechanism == ""


class TestMeme:
    """Meme model construction and serialization."""

    def test_default_id_is_generated(self):
        m = Meme()
        assert m.id.startswith("meme_")
        assert len(m.id) > 5

    def test_default_created_at(self):
        m = Meme()
        assert m.created_at is not None
        assert isinstance(m.created_at, datetime)

    def test_custom_id_preserved(self):
        m = Meme(id="custom_id")
        assert m.id == "custom_id"

    def test_default_values(self):
        m = Meme()
        assert m.text == ""
        assert m.source == MemeSource.AI
        assert m.base_score == 0.7
        assert m.current_score == 0.7
        assert m.is_active is True
        assert m.resurrection_count == 0
        assert m.use_count == 0
        assert m.source_platform == "internal"
        assert m.review_status == "pending"

    def test_to_dict(self):
        m = Meme(
            text="测试梗",
            context_hint="测试时使用",
            tags=["test", "debug"],
            base_score=0.8,
            cognitive_analysis=CognitiveAnalysis(humor_mechanism="谐音"),
        )
        d = m.to_dict()
        assert d["id"] == m.id
        assert d["text"] == "测试梗"
        assert d["tags"] == ["test", "debug"]
        assert d["base_score"] == 0.8
        assert d["cognitive_analysis"]["humor_mechanism"] == "谐音"
        assert d["source"] == "ai"

    def test_to_dict_no_cognitive(self):
        m = Meme(text="simple")
        d = m.to_dict()
        assert "cognitive_analysis" not in d

    def test_last_used_at_serialization(self):
        dt = datetime(2026, 5, 10, 12, 0, 0)
        m = Meme(text="ts", last_used_at=dt)
        d = m.to_dict()
        assert d["last_used_at"] == dt.isoformat()

    def test_last_used_at_none(self):
        m = Meme(text="no_last_use")
        d = m.to_dict()
        assert d["last_used_at"] is None

    def test_full_cycle(self):
        """to_dict → dict can reconstruct a Meme (manual)."""
        m = Meme(
            text="循环测试",
            context_hint="任何场景",
            source=MemeSource.USER,
            tags=["cycle"],
            base_score=0.9,
            current_score=0.85,
            use_count=3,
            review_status="good",
        )
        d = m.to_dict()
        assert d["text"] == "循环测试"
        assert d["source"] == "user"
        assert d["use_count"] == 3
        assert d["review_status"] == "good"
