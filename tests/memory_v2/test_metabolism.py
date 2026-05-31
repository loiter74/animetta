"""Tests for MetabolismScheduler."""

import math
from datetime import datetime, timezone

from animetta.memory.v2.atom import MemoryAtom, Layer
from animetta.memory.v2.metabolism import MetabolismScheduler


class TestSalienceCalculation:
    def test_fresh_atom_default_salience(self):
        atom = MemoryAtom(
            id="a1", layer=Layer.RAW, content="test",
            occurred_at=datetime.now(timezone.utc),
            confidence=0.5,
        )
        salience = MetabolismScheduler.compute_salience(atom)
        assert math.isclose(salience, 0.5, rel_tol=0.15)

    def test_high_confidence_increases_salience(self):
        high = MemoryAtom(
            id="h1", layer=Layer.RAW, content="important",
            occurred_at=datetime.now(timezone.utc), confidence=0.9,
        )
        low = MemoryAtom(
            id="l1", layer=Layer.RAW, content="trivial",
            occurred_at=datetime.now(timezone.utc), confidence=0.2,
        )
        assert MetabolismScheduler.compute_salience(high) > MetabolismScheduler.compute_salience(low)

    def test_retrieval_boosts_salience(self):
        retrieved = MemoryAtom(
            id="r1", layer=Layer.RAW, content="recalled",
            occurred_at=datetime.now(timezone.utc), retrieval_count=10,
        )
        fresh = MemoryAtom(
            id="f1", layer=Layer.RAW, content="fresh",
            occurred_at=datetime.now(timezone.utc), retrieval_count=0,
        )
        assert MetabolismScheduler.compute_salience(retrieved) > MetabolismScheduler.compute_salience(fresh)


class TestAdaptiveThreshold:
    def test_low_watermark_relaxed(self):
        threshold = MetabolismScheduler.adaptive_threshold(atom_count=25, capacity=100)
        assert threshold <= 0.02

    def test_high_watermark_aggressive(self):
        threshold = MetabolismScheduler.adaptive_threshold(atom_count=90, capacity=100)
        assert threshold >= 0.15

    def test_mid_watermark_moderate(self):
        threshold = MetabolismScheduler.adaptive_threshold(atom_count=60, capacity=100)
        assert 0.05 < threshold < 0.20

    def test_full_capacity_max_threshold(self):
        threshold = MetabolismScheduler.adaptive_threshold(atom_count=100, capacity=100)
        assert threshold == 0.20
