"""Tests for MemoryScorer — importance scoring, emotion weighting, decay."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from src.anima.memory.models.turns import MemoryTurn
from src.anima.memory.search.scorer import (
    MemoryScorer,
    EMOTION_INTENSITY,
    EMOTION_BOOST_FACTOR,
    DECAY_BASE_RATE,
    DECAY_ARCHIVE_THRESHOLD,
)


def _turn(user_input: str = "", emotions: list[str] | None = None) -> MemoryTurn:
    return MemoryTurn(
        turn_id="t1",
        session_id="s1",
        timestamp=datetime.now(),
        user_input=user_input,
        agent_response="ok",
        emotions=emotions or [],
    )


class TestMemoryScorer:
    """Conversation importance scoring."""

    def test_base_score(self):
        score = MemoryScorer().score(_turn("hi"))
        assert score == pytest.approx(0.3)

    def test_key_info_bonus(self):
        """Patterns like '我叫...' get +0.15."""
        score = MemoryScorer().score(_turn("我叫小明"))
        assert score == pytest.approx(0.45)

    def test_length_reward(self):
        """Input > 50 chars gets +0.1."""
        score = MemoryScorer().score(_turn("a" * 60))
        assert score == pytest.approx(0.4)

    def test_short_question_penalty(self):
        """Short questions ending with '?' get -0.1."""
        score = MemoryScorer().score(_turn("你好吗?"))
        assert score == pytest.approx(0.2)

    def test_long_question_no_penalty(self):
        """Long questions (len >= 15) do NOT get the -0.1 short-question penalty."""
        # 15+ character question with '?' — condition: len < 15 is False, no penalty
        long_q = "how should we design this feature?"  # len=36, >= 15, ends with ?
        score = MemoryScorer().score(_turn(long_q))
        # base(0.3) + key_info(0) + length(0 if <=50 else +0.1) + no penalty = 0.3
        assert score == pytest.approx(0.3, abs=0.01)

    def test_score_clamped_to_zero(self):
        """Score never goes below 0.0."""
        score = MemoryScorer().score(_turn("?"))
        # base(0.3) - penalty(0.1) = 0.2 — still above zero
        assert score >= 0.0

    def test_score_clamped_to_one(self):
        """Score never exceeds 1.0."""
        turn = _turn("我叫小明" + "a" * 100)
        score = MemoryScorer().score(turn)
        assert score <= 1.0

    def test_key_info_chinese_patterns(self):
        test_cases = [
            "我的名字是小红",
            "我今年25",
            "我住在北京",
            "我的职业是工程师",
            "我非常喜欢音乐",
            "我希望去旅行",
            "记住我的生日是五月",
            "别忘了带钥匙",
        ]
        scorer = MemoryScorer()
        for text in test_cases:
            score = scorer.score(_turn(text))
            assert score >= 0.4, f"Failed for: {text}"

    def test_should_store_above_threshold(self):
        scorer = MemoryScorer()
        assert scorer.should_store(0.5) is True
        assert scorer.should_store(0.3) is True
        assert scorer.should_store(0.29) is False

    def test_multiple_key_patterns_only_once(self):
        """Key info bonus is added only once even with multiple matches."""
        scorer = MemoryScorer()
        # Input with 50+ chars to also get length reward
        score = scorer.score(_turn("我叫小明 我住在北京 我今年25 " + "a" * 35))
        # base(0.3) + key_info(0.15) + length(0.1) = 0.55
        assert score == pytest.approx(0.55)


class TestEmotionScoring:
    """Emotion intensity and weight calculations."""

    def test_emotion_intensity_mapping(self):
        assert EMOTION_INTENSITY["neutral"] == 0.1
        assert EMOTION_INTENSITY["happy"] == 0.7
        assert EMOTION_INTENSITY["angry"] == 0.9

    def test_emotion_intensity_no_emotions(self):
        assert MemoryScorer.emotion_intensity(_turn()) == 0.0

    def test_emotion_intensity_max(self):
        turn = _turn(emotions=["happy", "angry"])
        assert MemoryScorer.emotion_intensity(turn) == 0.9  # angry is higher

    def test_emotion_weight_no_emotion(self):
        assert MemoryScorer.emotion_weight(None) == 1.0
        assert MemoryScorer.emotion_weight(0.0) == 1.0

    def test_emotion_weight_max_boost(self):
        weight = MemoryScorer.emotion_weight(1.0)
        assert weight == pytest.approx(1.0 + EMOTION_BOOST_FACTOR)

    def test_emotion_weight_mid(self):
        weight = MemoryScorer.emotion_weight(0.5)
        assert weight == pytest.approx(1.0 + 0.5 * EMOTION_BOOST_FACTOR)

    def test_emotion_decay_factor_no_emotion(self):
        assert MemoryScorer.emotion_decay_factor(None) == 0.2
        assert MemoryScorer.emotion_decay_factor(0.0) == 0.2

    def test_emotion_decay_factor_high(self):
        """High emotion → slower decay (factor closer to 1)."""
        assert MemoryScorer.emotion_decay_factor(1.0) == 1.0

    def test_emotion_decay_factor_mid(self):
        factor = MemoryScorer.emotion_decay_factor(0.5)
        assert factor == pytest.approx(0.5)


class TestDecay:
    """Memory decay computation."""

    def test_compute_decay_no_date(self):
        assert MemoryScorer.compute_decay(None) == 1.0

    def test_compute_decay_just_created(self):
        now = datetime.now(timezone.utc).isoformat()
        decay = MemoryScorer.compute_decay(now)
        assert decay == pytest.approx(1.0, abs=0.01)

    def test_compute_decay_old_memory(self):
        """Old memory without retrieval or emotion decays significantly."""
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        decay = MemoryScorer.compute_decay(old, retrieval_count=0, emotion_value=None)
        assert decay < 0.5

    def test_compute_decay_retrieval_slows_decay(self):
        """Frequently retrieved memories decay slower."""
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        d1 = MemoryScorer.compute_decay(old, retrieval_count=1, emotion_value=0.0)
        d2 = MemoryScorer.compute_decay(old, retrieval_count=10, emotion_value=0.0)
        assert d2 > d1

    def test_compute_decay_emotion_slows_decay(self):
        """High-emotion memories decay slower."""
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        d1 = MemoryScorer.compute_decay(old, retrieval_count=1, emotion_value=0.1)
        d2 = MemoryScorer.compute_decay(old, retrieval_count=1, emotion_value=1.0)
        assert d2 > d1

    def test_invalid_date_returns_one(self):
        assert MemoryScorer.compute_decay("not-a-date") == 1.0

    def test_future_date_returns_one(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        decay = MemoryScorer.compute_decay(future)
        assert decay == pytest.approx(1.0, abs=0.01)


class TestMemoryScore:
    """Combined memory_score computation."""

    def test_memory_score_defaults(self):
        final, decay, archived = MemoryScorer.memory_score()
        assert 0.0 <= final <= 1.0
        assert 0.0 < decay <= 1.0

    def test_memory_score_archive_threshold(self):
        """Old memories with low confidence get archived."""
        old = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        final, decay, archived = MemoryScorer.memory_score(
            confidence=0.3, created_at=old, retrieval_count=0, emotion_value=0.0
        )
        assert archived is True
        assert final < DECAY_ARCHIVE_THRESHOLD

    def test_memory_score_not_archived(self):
        now = datetime.now(timezone.utc).isoformat()
        final, decay, archived = MemoryScorer.memory_score(
            confidence=1.0, created_at=now, retrieval_count=10, emotion_value=1.0
        )
        assert archived is False

    def test_memory_score_components(self):
        now = datetime.now(timezone.utc).isoformat()
        final, decay, archived = MemoryScorer.memory_score(
            confidence=0.8, created_at=now, retrieval_count=3, emotion_value=0.5
        )
        assert final > 0.0
        assert decay > 0.0
        # final = confidence * decay * emotion_boost
        expected_decay = MemoryScorer.compute_decay(now, 3, 0.5)
        expected_boost = MemoryScorer.emotion_weight(0.5)
        assert final == pytest.approx(0.8 * expected_decay * expected_boost)
