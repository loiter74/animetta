"""Tests for MemePool — meme lifecycle engine with time-decay scoring."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest



# ── fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def fake_store():
    """Fake MemeStore with in-memory lists."""
    store = MagicMock()
    active: list[Meme] = []
    discarded: list[Meme] = []

    def _save(meme: Meme) -> str:
        meme.is_active = True
        active.append(meme)
        return meme.id

    def _discard(meme_id: str) -> None:
        for m in active:
            if m.id == meme_id:
                m.is_active = False
                active.remove(m)
                discarded.append(m)
                return

    def _resurrect(meme_id: str) -> None:
        for m in discarded:
            if m.id == meme_id:
                m.is_active = True
                discarded.remove(m)
                active.append(m)
                return

    store.save.side_effect = _save
    store.discard.side_effect = _discard
    store.resurrect.side_effect = _resurrect
    store.list_active.side_effect = lambda: list(active)
    store.list_discarded.side_effect = lambda: list(discarded)
    store.update = MagicMock()
    return store


@pytest.fixture
def pool(fake_store):
    """MemePool with fake store and default config."""
    return MemePool(store=fake_store, config={"max_active": 5, "k": 0.5, "t_half_days": 7})


@pytest.fixture
def pool_tiny(fake_store):
    """MemePool with tiny pool (max_active=2) for overflow tests."""
    return MemePool(store=fake_store, config={"max_active": 2})


# ── construction ─────────────────────────────────────────────────────────


class TestMemePoolConstruction:
    """MemePool initialisation with different configs."""

    def test_default_config(self, fake_store):
        pool = MemePool(store=fake_store)
        assert pool.max_active == 20
        assert pool.k == 0.5
        assert pool.t_half_days == 7
        assert pool.resurrection_threshold == 0.6
        assert pool.resurrection_bonus == 0.1
        assert pool.resurrection_max_bonuses == 3

    def test_custom_config(self, fake_store):
        pool = MemePool(store=fake_store, config={
            "max_active": 3, "k": 1.0, "t_half_days": 14,
            "resurrection_threshold": 0.8, "resurrection_bonus": 0.2,
            "resurrection_max_bonuses": 5, "persona_fit_threshold": 0.6,
        })
        assert pool.max_active == 3
        assert pool.k == 1.0
        assert pool.t_half_days == 14
        assert pool.resurrection_threshold == 0.8
        assert pool.resurrection_bonus == 0.2
        assert pool.resurrection_max_bonuses == 5
        assert pool.persona_fit_threshold == 0.6

    def test_empty_config_defaults(self, fake_store):
        pool = MemePool(store=fake_store, config={})
        assert pool.max_active == 20
        assert pool.resurrection_threshold == 0.6

    def test_with_search_fn(self, fake_store):
        search_fn = MagicMock(return_value=[])
        pool = MemePool(store=fake_store, search_fn=search_fn)
        assert pool._search_fn is search_fn


# ── add_meme ─────────────────────────────────────────────────────────────


class TestMemePoolAddMeme:
    """add_meme: insertion when pool has space vs when full."""

    def test_add_when_pool_has_space(self, pool):
        meme = pool.add_meme(text="hello world", context_hint="greeting")
        assert meme.id.startswith("meme_")
        assert meme.text == "hello world"
        assert meme.context_hint == "greeting"
        assert meme.source == MemeSource.AI
        assert meme.base_score == 0.7
        assert meme.is_active is True
        assert len(pool.get_active()) == 1

    def test_add_replaces_lowest_when_pool_full(self, pool_tiny, fake_store):
        # Fill the pool (max_active=2)
        m1 = pool_tiny.add_meme("high score")
        m1.base_score = 0.9
        m1.current_score = 0.9
        m2 = pool_tiny.add_meme("low score")
        m2.base_score = 0.3
        m2.current_score = 0.3

        # Add a third — should replace the lowest (m2)
        m3 = pool_tiny.add_meme("new meme")
        m3.base_score = 0.7
        m3.current_score = 0.7

        active = pool_tiny.get_active()
        assert len(active) == 2
        active_ids = {m.id for m in active}
        assert m1.id in active_ids
        assert m3.id in active_ids
        assert m2.id not in active_ids  # m2 was discarded

    def test_add_with_tags_and_source(self, pool):
        meme = pool.add_meme(text="bilibili meme", source=MemeSource.USER, tags=["funny", "viral"])
        assert meme.source == MemeSource.USER
        assert meme.tags == ["funny", "viral"]


# ── add_from_candidate ───────────────────────────────────────────────────


class TestMemePoolAddFromCandidate:
    """add_from_candidate: confidence-based acceptance."""

    def test_accepts_high_confidence_when_pool_has_space(self, pool):
        meme = pool.add_from_candidate("interesting", confidence=0.8)
        assert meme is not None
        assert meme.text == "interesting"
        assert meme.base_score == 0.9  # 0.8 + 0.1
        assert len(pool.get_active()) == 1

    def test_rejects_low_confidence_when_pool_full(self, pool_tiny, fake_store):
        # Fill pool
        pool_tiny.add_meme("m1")
        pool_tiny.add_meme("m2")

        result = pool_tiny.add_from_candidate("weak", confidence=0.3)
        assert result is None

    def test_accepts_high_confidence_even_when_pool_full(self, pool_tiny, fake_store):
        pool_tiny.add_meme("m1")
        pool_tiny.add_meme("m2")

        result = pool_tiny.add_from_candidate("strong", confidence=0.9)
        assert result is not None
        assert result.text == "strong"

    def test_confidence_capped_at_1(self, pool):
        meme = pool.add_from_candidate("very confident", confidence=1.0)
        assert meme is not None
        assert meme.base_score == 1.0


# ── select_for_context ──────────────────────────────────────────────────


class TestMemePoolSelectForContext:
    """select_for_context: context-aware meme selection."""

    def test_returns_none_when_no_active(self, pool):
        result = pool.select_for_context("hello")
        assert result is None

    def test_selects_best_match_by_text_overlap(self, pool):
        pool.add_meme("hello world", context_hint="greeting")
        pool.add_meme("lorem ipsum", context_hint="placeholder")
        pool.add_meme("goodbye", context_hint="farewell")

        result = pool.select_for_context("hello there friend")
        assert result is not None
        assert "hello" in result.text

    def test_skips_inactive_memes(self, pool):
        m1 = pool.add_meme("hello world")
        pool.add_meme("lorem ipsum")
        m1.is_active = False

        result = pool.select_for_context("hello")
        assert result is None  # No active meme matches "hello"

    def test_returns_none_on_empty_input(self, pool):
        pool.add_meme("hello world")
        result = pool.select_for_context("")
        assert result is None

    def test_ignores_text_input(self, pool):
        pool.add_meme("abc123xyz", context_hint="unique_trigger_phrase")

        result = pool.select_for_context("no overlap at all")
        assert result is None

    def test_source_platform_filter(self, pool):
        m_b = Meme(text="bilibili meme", source_platform="bilibili")
        m_i = Meme(text="internal meme", source_platform="internal")
        pool.store.save(m_b)
        pool.store.save(m_i)

        result = pool.select_for_context("meme", source_platform="bilibili")
        assert result is not None
        assert result.source_platform == "bilibili"

    def test_streaming_mode_prefers_active(self, pool):
        m1 = Meme(text="stream meme", is_active=True)
        m2 = Meme(text="inactive stream", is_active=False)
        pool.store.save(m1)
        pool.store.save(m2)

        result = pool.select_for_context("anything", personality_mode="streaming")
        assert result is not None
        assert result.text == "stream meme" or result.is_active

    def test_normal_mode_prefers_highest_score(self, pool):
        m1 = Meme(text="low score meme", base_score=0.3, current_score=0.3)
        m2 = Meme(text="high score meme", base_score=0.9, current_score=0.9)
        pool.store.save(m1)
        pool.store.save(m2)

        # Neither has context_hint set, both empty, so _context_match returns False
        # Add context_hint to make matching work
        m1.context_hint = "test"
        m2.context_hint = "test"

        result = pool.select_for_context("test")
        assert result is not None
        assert result.current_score == 0.9  # Higher score chosen


# ── score_after_use ──────────────────────────────────────────────────────


class TestMemePoolScoreAfterUse:
    """score_after_use: update meme score after interaction."""

    def test_updates_score(self, pool):
        meme = pool.add_meme("test meme")
        original_score = meme.base_score

        pool.score_after_use(meme.id, effectiveness=1.0)
        # base = 0.7 * original + 0.3 * 1.0 = 0.7*0.7 + 0.3 = 0.49 + 0.3 = 0.79
        expected = 0.7 * original_score + 0.3 * 1.0
        assert pytest.approx(meme.base_score, abs=0.01) == expected
        assert meme.use_count == 1
        assert meme.last_used_at is not None

    def test_does_nothing_for_unknown_id(self, pool):
        # Should not raise
        pool.score_after_use("nonexistent", effectiveness=0.5)

    def test_effectiveness_blended(self, pool):
        meme = pool.add_meme("another meme")
        pool.score_after_use(meme.id, effectiveness=0.5)
        expected = 0.7 * 0.7 + 0.3 * 0.5  # 0.49 + 0.15 = 0.64
        assert pytest.approx(meme.base_score, abs=0.01) == expected

    def test_increments_use_count(self, pool):
        meme = pool.add_meme("count test")
        assert meme.use_count == 0
        pool.score_after_use(meme.id, effectiveness=0.8)
        pool.score_after_use(meme.id, effectiveness=0.6)
        assert meme.use_count == 2


# ── maintain_pool ────────────────────────────────────────────────────────


class TestMemePoolMaintain:
    """maintain_pool: time-decay scoring and resurrection."""

    def test_decays_scores_over_time(self, pool):
        meme = pool.add_meme("old meme")
        meme.base_score = 0.9
        # Simulate old last_used_at
        meme.last_used_at = datetime.now() - timedelta(days=30)
        meme.current_score = 0.9

        pool.maintain_pool()
        assert meme.current_score < 0.9  # Score decayed
        assert meme.current_score > 0.0

    def test_discards_low_score_memes_when_over_max(self, pool_tiny, fake_store):
        # Fill pool (max_active=2)
        m1 = pool_tiny.add_meme("high")
        m1.base_score = 0.9
        m1.current_score = 0.9
        m2 = pool_tiny.add_meme("mid")
        m2.base_score = 0.6
        m2.current_score = 0.6
        # Add a third manually (bypass overflow logic)
        m3 = Meme(text="low", base_score=0.2, current_score=0.2)
        pool_tiny.store.save(m3)

        # Now 3 active but max is 2 — maintain should discard lowest
        pool_tiny.maintain_pool()

        active = pool_tiny.get_active()
        assert len(active) <= 2
        low_still_active = any(m.id == m3.id for m in active)
        assert not low_still_active  # m3 (lowest) was discarded

    def test_resurrects_high_score_discarded_memes(self, pool, fake_store):
        # Create a discarded meme with high potential score
        dm = Meme(
            text="resurrect me",
            base_score=0.9,
            current_score=0.9,
            is_active=False,
        )
        # Set created_at to recent so effective score stays high
        dm.created_at = datetime.now()
        dm.last_used_at = datetime.now()
        fake_store.list_discarded.side_effect = lambda: [dm]
        # Only this one meme active, so pool has space
        pool.add_meme("filler")

        count_before = dm.resurrection_count
        pool.maintain_pool()

        assert dm.is_active is True
        assert dm.resurrection_count == count_before + 1

    def test_no_resurrection_when_pool_full(self, pool_tiny, fake_store):
        # Fill pool to max
        pool_tiny.add_meme("a")
        pool_tiny.add_meme("b")

        dm = Meme(
            text="should not resurrect",
            base_score=0.9,
            current_score=0.9,
            is_active=False,
        )
        dm.created_at = datetime.now()
        dm.last_used_at = datetime.now()
        fake_store.list_discarded.side_effect = lambda: [dm]

        pool_tiny.maintain_pool()
        assert dm.is_active is False  # Pool full, no resurrection

    def test_resurrection_capped_by_max_bonuses(self, pool, fake_store):
        dm = Meme(
            text="max resurrections",
            base_score=0.9,
            current_score=0.9,
            is_active=False,
            resurrection_count=3,  # Already at max (default resurrection_max_bonuses=3)
        )
        dm.created_at = datetime.now()
        dm.last_used_at = datetime.now()
        fake_store.list_discarded.side_effect = lambda: [dm]
        pool.add_meme("filler")

        pool.maintain_pool()
        assert dm.is_active is False  # Max resurrections reached


# ── effective score ──────────────────────────────────────────────────────


class TestEffectiveScore:
    """_effective_score: time-decay calculation."""

    def test_no_decay_when_just_created(self, pool):
        meme = Meme(base_score=1.0)
        meme.created_at = datetime.now()
        meme.last_used_at = datetime.now()

        score = pool._effective_score(meme)
        assert pytest.approx(score, abs=0.05) == 1.0

    def test_half_decay_at_half_life(self, pool):
        meme = Meme(base_score=1.0)
        meme.last_used_at = datetime.now() - timedelta(days=pool.t_half_days)

        score = pool._effective_score(meme)
        # At t_half_days, sigmoid(0) = 0.5, so score ≈ 0.5
        assert pytest.approx(score, abs=0.05) == 0.5

    def test_near_zero_after_long_time(self, pool):
        meme = Meme(base_score=1.0)
        meme.last_used_at = datetime.now() - timedelta(days=365)

        score = pool._effective_score(meme)
        assert score < 0.01

    def test_uses_created_at_when_last_used_is_none(self, pool):
        meme = Meme(base_score=1.0)
        meme.created_at = datetime.now()
        meme.last_used_at = None

        score = pool._effective_score(meme)
        assert pytest.approx(score, abs=0.05) == 1.0

    def test_custom_k_and_half_life(self, fake_store):
        pool = MemePool(store=fake_store, config={"k": 1.0, "t_half_days": 3})
        meme = Meme(base_score=1.0)
        meme.last_used_at = datetime.now() - timedelta(days=3)

        score = pool._effective_score(meme)
        # At t_half_days=3 with k=1.0, sigmoid(0) = 0.5
        assert pytest.approx(score, abs=0.05) == 0.5


# ── text overlap ─────────────────────────────────────────────────────────


class TestTextOverlap:
    """_text_overlap: text matching logic."""

    def test_substring_containment(self):
        assert MemePool._text_overlap("hello world", "hello") is True
        assert MemePool._text_overlap("hi", "hello world") is False

    def test_case_insensitive(self):
        assert MemePool._text_overlap("Hello", "HELLO WORLD") is True

    def test_word_overlap_threshold(self):
        # "cat dog bird" ∩ "cat dog fish" = 2/3 overlap -> 66% > 25%
        assert MemePool._text_overlap("cat dog bird", "cat dog fish") is True

    def test_word_overlap_below_threshold(self):
        # "a b c d e" ∩ "a f g h i" = 1/5 overlap = 20% < 25% -> False
        assert MemePool._text_overlap("a b c d e", "a f g h i") is False

    def test_empty_strings(self):
        assert MemePool._text_overlap("", "hello") is False
        assert MemePool._text_overlap("hello", "") is False
        assert MemePool._text_overlap("", "") is False

    def test_punctuation_ignored(self):
        assert MemePool._text_overlap("hello world!", "world") is True
        assert MemePool._text_overlap("hello, world.", "hello") is True


# ── stats ────────────────────────────────────────────────────────────────


class TestMemePoolStats:
    """get_stats: pool statistics."""

    def test_empty_pool_stats(self, pool):
        stats = pool.get_stats()
        assert stats["total_active"] == 0
        assert stats["total_discarded"] == 0
        assert stats["average_score"] == 0.0
        assert stats["total_uses"] == 0

    def test_populated_pool_stats(self, pool):
        m1 = pool.add_meme("first")
        m1.base_score = 0.8
        m1.current_score = 0.8
        m2 = pool.add_meme("second")
        m2.base_score = 0.6
        m2.current_score = 0.6
        m1.current_score = 0.8
        m2.current_score = 0.6

        stats = pool.get_stats()
        assert stats["total_active"] == 2
        assert stats["max_active"] == 5
        assert stats["average_score"] == 0.7

    def test_config_included_in_stats(self, pool):
        stats = pool.get_stats()
        assert "config" in stats
        assert stats["config"]["k"] == 0.5
        assert stats["config"]["t_half_days"] == 7
