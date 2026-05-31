"""Unit tests: emotion-weighted retrieval scoring."""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from animetta.memory.search.scorer import (
    MemoryScorer,
    EMOTION_INTENSITY,
    EMOTION_BOOST_FACTOR,
)


class TestEmotionIntensity:
    def test_neutral_gives_low_intensity(self):
        assert EMOTION_INTENSITY["neutral"] == 0.1

    def test_angry_gives_high_intensity(self):
        assert EMOTION_INTENSITY["angry"] > 0.8

    def test_happy_is_moderate(self):
        assert 0.6 < EMOTION_INTENSITY["happy"] < 0.9


class TestEmotionWeight:
    def test_no_emotion_gives_no_boost(self):
        assert MemoryScorer.emotion_weight(None) == 1.0
        assert MemoryScorer.emotion_weight(0.0) == 1.0

    def test_max_emotion_gives_max_boost(self):
        weight = MemoryScorer.emotion_weight(1.0)
        assert weight == 1.0 + EMOTION_BOOST_FACTOR

    def test_half_emotion_gives_half_boost(self):
        weight = MemoryScorer.emotion_weight(0.5)
        expected = 1.0 + 0.5 * EMOTION_BOOST_FACTOR
        assert weight == expected

    def test_boost_never_exceeds_1_5(self):
        weight = MemoryScorer.emotion_weight(0.999)
        assert weight <= 1.5


class TestEmotionDecayFactor:
    def test_no_emotion_fast_decay(self):
        factor = MemoryScorer.emotion_decay_factor(None)
        assert factor < 0.5

    def test_high_emotion_slow_decay(self):
        factor = MemoryScorer.emotion_decay_factor(1.0)
        assert factor == 1.0

    def test_factor_in_valid_range(self):
        for v in [0.0, 0.3, 0.5, 0.8, 0.99]:
            factor = MemoryScorer.emotion_decay_factor(v)
            assert 0.0 < factor <= 1.0
