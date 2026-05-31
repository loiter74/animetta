"""Unit tests for the memory evolution system.

Covers:
- AsyncScheduler (periodic task scheduling)
- MemePool (meme lifecycle with time-decay scoring)
"""

from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest


class _FakeMemeStore:
    """In-memory MemeStore for testing. Imports Meme only on demand."""

    def __init__(self):
        self._active: Dict[str, Any] = {}
        self._discarded: list[Any] = []

    def list_active(self):
        return [m for m in self._active.values() if m.is_active]

    def list_discarded(self):
        return self._discarded

    def save(self, meme):
        self._active[meme.id] = meme

    def update(self, meme):
        self._active.pop(meme.id, None)
        self._discarded[:] = [m for m in self._discarded if m.id != meme.id]
        if meme.is_active:
            self._active[meme.id] = meme
        else:
            self._discarded.append(meme)

    def discard(self, meme_id):
        if meme_id in self._active:
            meme = self._active.pop(meme_id)
            meme.is_active = False
            self._discarded.append(meme)

    def resurrect(self, meme_id):
        for i, m in enumerate(self._discarded):
            if m.id == meme_id:
                meme = self._discarded.pop(i)
                meme.is_active = True
                self._active[meme_id] = meme
                return


# ═══════════════════════════════════════════════════════════════
# AsyncScheduler tests
# ═══════════════════════════════════════════════════════════════


class TestAsyncScheduler:
    """Tests for AsyncScheduler periodic task scheduling."""

    @pytest.mark.asyncio
    async def test_add_task(self):

        scheduler = AsyncScheduler()

        async def dummy():
            pass

        scheduler.add_task("alpha", dummy, interval=10, timeout=5)
        metrics = scheduler.get_metrics()
        names = [m.name for m in metrics]

        assert "alpha" in names
        assert len(metrics) == 1

    @pytest.mark.asyncio
    async def test_task_execution(self):

        scheduler = AsyncScheduler()
        counter: list[int] = [0]

        async def count():
            counter[0] += 1

        scheduler.add_task("counter", count, interval=0.1, timeout=10)
        await scheduler.start()
        await asyncio.sleep(3)
        await scheduler.stop()

        assert counter[0] > 0

    @pytest.mark.asyncio
    async def test_task_timeout(self):

        scheduler = AsyncScheduler()

        async def slow():
            await asyncio.sleep(100)

        scheduler.add_task("slow", slow, interval=0.1, timeout=0.02)
        await scheduler.start()
        await asyncio.sleep(3)
        await scheduler.stop()

        metrics = scheduler.get_task_metrics("slow")
        assert metrics.failure_count > 0

    @pytest.mark.asyncio
    async def test_multiple_tasks(self):

        scheduler = AsyncScheduler()
        counters: dict[str, list[int]] = {"a": [0], "b": [0], "c": [0]}

        def make_counter(key: str):
            async def count():
                counters[key][0] += 1
            return count

        scheduler.add_task("a", make_counter("a"), interval=0.1, timeout=10)
        scheduler.add_task("b", make_counter("b"), interval=0.1, timeout=10)
        scheduler.add_task("c", make_counter("c"), interval=0.1, timeout=10)
        await scheduler.start()
        await asyncio.sleep(3.5)
        await scheduler.stop()

        assert counters["a"][0] > 0
        assert counters["b"][0] > 0
        assert counters["c"][0] > 0

    @pytest.mark.asyncio
    async def test_graceful_stop(self):

        scheduler = AsyncScheduler()

        async def dummy():
            pass

        scheduler.add_task("dummy", dummy, interval=10, timeout=5)
        await scheduler.start()
        await scheduler.stop()

        assert not scheduler._running



# ═══════════════════════════════════════════════════════════════
# MemePool tests
# ═══════════════════════════════════════════════════════════════


class TestMemePool:
    """Tests for MemePool meme lifecycle engine."""

    def test_add_meme(self):

        store = _FakeMemeStore()
        pool = MemePool(store, {"max_active": 10})

        m = pool.add_meme("cool meme", context_hint="testing")
        active = pool.get_active()

        assert len(active) == 1
        assert active[0].id == m.id
        assert active[0].text == "cool meme"
        assert active[0].context_hint == "testing"

    def test_effective_score_recent(self):

        store = _FakeMemeStore()
        pool = MemePool(store)

        m = Meme(text="recent", base_score=0.7, current_score=0.7, created_at=datetime.now())
        now = datetime.now()
        score = pool._effective_score(m, now)

        assert score <= m.base_score
        assert score > 0.5

    def test_effective_score_old(self):

        store = _FakeMemeStore()
        pool = MemePool(store)

        old_time = datetime.now() - timedelta(days=30)
        m = Meme(text="old", base_score=0.7, current_score=0.7, last_used_at=old_time)
        now = datetime.now()
        score = pool._effective_score(m, now)

        assert score < 0.1
        assert score < m.base_score

    def test_pool_max_active(self):

        store = _FakeMemeStore()
        pool = MemePool(store, {"max_active": 10})

        for i in range(15):
            pool.add_meme(f"meme_{i}", context_hint=f"hint_{i}")

        active = pool.get_active()
        assert len(active) <= 10

    def test_context_match(self):

        store = _FakeMemeStore()
        pool = MemePool(store)

        assert pool._context_match("weather is nice today", "weather")
        assert pool._context_match("Hello World", "hello")
        assert not pool._context_match("weather is nice today", "programming")
        assert not pool._context_match("hello", "")
        assert pool._context_match("TypeScript type system", "typescript")

    def test_add_from_candidate_accepted(self):

        store = _FakeMemeStore()
        pool = MemePool(store, {"max_active": 10})

        m = pool.add_from_candidate("候选梗", confidence=0.8)
        assert m is not None
        assert m.text == "候选梗"
        assert m.base_score == pytest.approx(0.9)

    def test_add_from_candidate_rejected_low_confidence(self):

        store = _FakeMemeStore()
        pool = MemePool(store, {"max_active": 1})

        pool.add_meme("existing")
        m = pool.add_from_candidate("candidate", confidence=0.3)
        assert m is None

    def test_score_after_use(self):

        store = _FakeMemeStore()
        pool = MemePool(store)

        m = pool.add_meme("test meme")
        pool.score_after_use(m.id, effectiveness=1.0)

        assert m.use_count == 1
        assert m.last_used_at is not None

    def test_maintain_pool_discards_excess(self):

        store = _FakeMemeStore()
        pool = MemePool(store, {"max_active": 3})

        for i in range(5):
            pool.add_meme(f"meme_{i}")
        pool.maintain_pool()

        active = pool.get_active()
        assert len(active) <= 3

    def test_select_for_context_returns_meme(self):

        store = _FakeMemeStore()
        pool = MemePool(store)

        pool.add_meme("testing meme", context_hint="test code")
        selected = pool.select_for_context("today I write test code", personality_mode="normal")

        assert selected is not None
        assert selected.text == "testing meme"

    def test_select_for_context_no_match(self):

        store = _FakeMemeStore()
        pool = MemePool(store)

        pool.add_meme("coding meme", context_hint="programming debugging")
        # "baking bread recipe" has zero 2-char overlap with "programming debugging coding meme"
        selected = pool.select_for_context("baking bread recipe", personality_mode="normal")

        assert selected is None

    def test_get_stats(self):

        store = _FakeMemeStore()
        pool = MemePool(store)

        for i in range(3):
            pool.add_meme(f"meme_{i}")

        stats = pool.get_stats()
        assert stats["total_active"] == 3
        assert stats["max_active"] == 10
        assert stats["total_discarded"] == 0
