"""Unit tests: memory decay functions."""

import os, sys
from datetime import datetime, timezone, timedelta

import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from animetta.memory.search.scorer import (
    MemoryScorer,
    DECAY_BASE_RATE,
    DECAY_ARCHIVE_THRESHOLD,
)


class TestComputeDecay:
    def test_no_date_returns_one(self):
        assert MemoryScorer.compute_decay(None) == 1.0

    def test_just_created_returns_one(self):
        now = datetime.now(timezone.utc).isoformat()
        assert MemoryScorer.compute_decay(now) == pytest.approx(1.0, abs=0.001)

    def test_old_memory_decays(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        decay = MemoryScorer.compute_decay(old)
        assert decay < 0.5, f"30-day memory should be decayed, got {decay}"

    def test_high_emotion_retards_decay(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        plain = MemoryScorer.compute_decay(old, retrieval_count=0, emotion_value=0.0)
        emotional = MemoryScorer.compute_decay(old, retrieval_count=0, emotion_value=1.0)
        assert emotional > plain, f"emotional memory should decay slower: {emotional} vs {plain}"

    def test_frequent_retrieval_retards_decay(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        never = MemoryScorer.compute_decay(old, retrieval_count=0, emotion_value=0.5)
        frequent = MemoryScorer.compute_decay(old, retrieval_count=10, emotion_value=0.5)
        assert frequent > never, f"frequently retrieved should decay slower: {frequent} vs {never}"

    def test_decay_in_valid_range(self):
        old = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        decay = MemoryScorer.compute_decay(old, retrieval_count=0, emotion_value=0.0)
        assert 0.0 <= decay <= 1.0


class TestMemoryScore:
    def test_high_confidence_new_memory_not_archived(self):
        now = datetime.now(timezone.utc).isoformat()
        score, decay, archived = MemoryScorer.memory_score(
            confidence=0.9, created_at=now, retrieval_count=0, emotion_value=None
        )
        assert score > 0.7
        assert not archived

    def test_low_confidence_old_memory_archived(self):
        old = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
        score, decay, archived = MemoryScorer.memory_score(
            confidence=0.4, created_at=old, retrieval_count=0, emotion_value=None
        )
        assert archived or score < DECAY_ARCHIVE_THRESHOLD * 2

    def test_archived_below_threshold(self):
        old = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        _, _, archived = MemoryScorer.memory_score(
            confidence=0.3, created_at=old, retrieval_count=0, emotion_value=0.0
        )
        assert archived

    def test_emotion_and_retrieval_prevent_archive(self):
        old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        _, _, archived_no_protection = MemoryScorer.memory_score(
            confidence=0.5, created_at=old, retrieval_count=0, emotion_value=0.0
        )
        _, _, archived_with_protection = MemoryScorer.memory_score(
            confidence=0.5, created_at=old, retrieval_count=20, emotion_value=0.9
        )
        # With protection should be less likely to archive
        assert archived_with_protection <= archived_no_protection
