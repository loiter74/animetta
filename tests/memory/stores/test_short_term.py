"""Tests for ShortTermMemory — FIFO eviction, session isolation."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.anima.memory.models.turns import MemoryTurn
from src.anima.memory.stores.short_term import ShortTermMemory


def _make_turn(session_id: str, text: str, idx: int = 0) -> MemoryTurn:
    return MemoryTurn(
        turn_id=f"t_{idx}",
        session_id=session_id,
        timestamp=datetime.now(),
        user_input=text,
        agent_response=f"response_{idx}",
    )


class TestShortTermMemory:
    """ShortTermMemory append / get / clear / eviction."""

    def test_append_and_get_recent(self):
        mem = ShortTermMemory(max_turns=20)
        t1 = _make_turn("s1", "hello", 1)
        mem.append("s1", t1)
        recent = mem.get_recent("s1", 5)
        assert len(recent) == 1
        assert recent[0].turn_id == "t_1"

    def test_get_recent_returns_chronological_order(self):
        mem = ShortTermMemory(max_turns=20)
        for i in range(3):
            mem.append("s1", _make_turn("s1", f"msg{i}", i))
        recent = mem.get_recent("s1", 5)
        assert [t.turn_id for t in recent] == ["t_0", "t_1", "t_2"]

    def test_get_recent_respects_max_turns_param(self):
        mem = ShortTermMemory(max_turns=20)
        for i in range(10):
            mem.append("s1", _make_turn("s1", f"msg{i}", i))
        recent = mem.get_recent("s1", 3)
        assert len(recent) == 3
        assert recent[-1].turn_id == "t_9"

    def test_get_recent_empty_session(self):
        mem = ShortTermMemory(max_turns=20)
        assert mem.get_recent("nonexistent", 5) == []

    def test_fifo_eviction(self):
        """When max_turns is exceeded, oldest turns are evicted."""
        mem = ShortTermMemory(max_turns=3)
        for i in range(5):
            mem.append("s1", _make_turn("s1", f"msg{i}", i))
        recent = mem.get_recent("s1", 10)
        assert len(recent) == 3
        assert recent[0].turn_id == "t_2"  # t_0 and t_1 evicted

    def test_session_isolation(self):
        """Different sessions don't interfere with each other."""
        mem = ShortTermMemory(max_turns=10)
        mem.append("s1", _make_turn("s1", "a", 1))
        mem.append("s2", _make_turn("s2", "b", 2))
        assert len(mem.get_recent("s1", 10)) == 1
        assert len(mem.get_recent("s2", 10)) == 1

    def test_clear_session(self):
        mem = ShortTermMemory(max_turns=10)
        mem.append("s1", _make_turn("s1", "x", 1))
        mem.append("s1", _make_turn("s1", "y", 2))
        mem.clear("s1")
        assert mem.get_recent("s1", 10) == []

    def test_clear_all(self):
        mem = ShortTermMemory(max_turns=10)
        mem.append("s1", _make_turn("s1", "a", 1))
        mem.append("s2", _make_turn("s2", "b", 2))
        mem.clear_all()
        assert mem.get_session_ids() == []

    def test_get_turn_count(self):
        mem = ShortTermMemory(max_turns=10)
        assert mem.get_turn_count("s1") == 0
        mem.append("s1", _make_turn("s1", "x", 1))
        mem.append("s1", _make_turn("s1", "y", 2))
        assert mem.get_turn_count("s1") == 2

    def test_get_session_ids(self):
        mem = ShortTermMemory(max_turns=10)
        mem.append("s1", _make_turn("s1", "a", 1))
        mem.append("s2", _make_turn("s2", "b", 2))
        assert sorted(mem.get_session_ids()) == ["s1", "s2"]
