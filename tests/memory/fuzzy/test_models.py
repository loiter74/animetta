"""Tests for FuzzyMemory, InvertedIndexEntry, and Granularity models."""

from __future__ import annotations

from datetime import datetime

import pytest



class TestGranularity:
    """Granularity enum values and usage."""

    def test_values_exist(self):
        assert Granularity.FACT.value == "fact"
        assert Granularity.PERSONA.value == "persona"
        assert Granularity.EVENT.value == "event"

    def test_all_levels_covered(self):
        assert len(Granularity) == 3

    def test_from_string(self):
        assert Granularity("fact") == Granularity.FACT
        assert Granularity("persona") == Granularity.PERSONA
        assert Granularity("event") == Granularity.EVENT

    def test_invalid_granularity_raises(self):
        with pytest.raises(ValueError):
            Granularity("invalid")

    def test_is_str_enum(self):
        assert isinstance(Granularity.FACT, str)
        assert Granularity.FACT == "fact"


class TestFuzzyMemory:
    """FuzzyMemory dataclass — construction, defaults, serialization."""

    def test_default_id_is_generated(self):
        fm = FuzzyMemory()
        assert fm.id.startswith("fuzzy_")
        assert len(fm.id) == 18  # "fuzzy_" + 12 hex chars

    def test_default_created_at(self):
        fm = FuzzyMemory()
        assert fm.created_at is not None
        assert isinstance(fm.created_at, datetime)

    def test_default_values(self):
        fm = FuzzyMemory()
        assert fm.session_id == ""
        assert fm.text == ""
        assert fm.granularity == Granularity.EVENT
        assert fm.confidence == 0.7
        assert fm.source_turn_ids == []
        assert fm.last_injected_at is None
        assert fm.injection_count == 0

    def test_custom_values_override_defaults(self):
        fm = FuzzyMemory(
            text="I remember the user likes TypeScript",
            granularity=Granularity.FACT,
            confidence=0.9,
            session_id="sess_001",
            source_turn_ids=["turn_1", "turn_2"],
            injection_count=5,
        )
        assert fm.text == "I remember the user likes TypeScript"
        assert fm.granularity == Granularity.FACT
        assert fm.confidence == 0.9
        assert fm.session_id == "sess_001"
        assert fm.source_turn_ids == ["turn_1", "turn_2"]
        assert fm.injection_count == 5

    def test_custom_id_preserved(self):
        fm = FuzzyMemory(id="my_custom_id")
        assert fm.id == "my_custom_id"

    def test_custom_created_at_preserved(self):
        dt = datetime(2025, 1, 15, 10, 30, 0)
        fm = FuzzyMemory(created_at=dt)
        assert fm.created_at == dt

    def test_to_dict_basic(self):
        fm = FuzzyMemory(
            id="fuzzy_abc",
            session_id="sess_001",
            text="The user enjoys hiking",
            granularity=Granularity.FACT,
            confidence=0.85,
            source_turn_ids=["t1"],
        )
        d = fm.to_dict()
        assert d["id"] == "fuzzy_abc"
        assert d["session_id"] == "sess_001"
        assert d["text"] == "The user enjoys hiking"
        assert d["granularity"] == "fact"
        assert d["confidence"] == 0.85
        assert d["source_turn_ids"] == ["t1"]
        assert d["injection_count"] == 0

    def test_to_dict_with_none_fields(self):
        dt = datetime(2025, 6, 1, 0, 0, 0)
        fm = FuzzyMemory(text="simple", created_at=dt, last_injected_at=None)
        d = fm.to_dict()
        assert d["created_at"] == "2025-06-01T00:00:00"
        assert d["last_injected_at"] is None

    def test_to_dict_with_timestamps(self):
        dt_created = datetime(2026, 3, 1, 12, 0, 0)
        dt_injected = datetime(2026, 4, 15, 8, 30, 0)
        fm = FuzzyMemory(
            text="timestamped memory",
            created_at=dt_created,
            last_injected_at=dt_injected,
        )
        d = fm.to_dict()
        assert d["created_at"] == "2026-03-01T12:00:00"
        assert d["last_injected_at"] == "2026-04-15T08:30:00"

    def test_each_granularity_level_works(self):
        for gran in (Granularity.FACT, Granularity.PERSONA, Granularity.EVENT):
            fm = FuzzyMemory(
                text=f"{gran.value} level memory",
                granularity=gran,
            )
            assert fm.granularity == gran
            d = fm.to_dict()
            assert d["granularity"] == gran.value

    def test_multiple_memories_have_unique_ids(self):
        fm1 = FuzzyMemory(text="memory one")
        fm2 = FuzzyMemory(text="memory two")
        assert fm1.id != fm2.id

    def test_confidence_bounds_are_not_enforced_by_model(self):
        """FuzzyMemory allows any float confidence; validation is caller's responsibility."""
        fm = FuzzyMemory(text="overconfident", confidence=1.5)
        assert fm.confidence == 1.5
        fm2 = FuzzyMemory(text="underconfident", confidence=-0.3)
        assert fm2.confidence == -0.3

    def test_source_turn_ids_empty_by_default(self):
        fm = FuzzyMemory(text="no sources")
        assert fm.source_turn_ids == []
        assert isinstance(fm.source_turn_ids, list)

    def test_injection_count_starts_at_zero(self):
        fm = FuzzyMemory(text="fresh memory")
        assert fm.injection_count == 0

    def test_session_id_defaults_to_empty(self):
        fm = FuzzyMemory(text="orphan memory")
        assert fm.session_id == ""


class TestInvertedIndexEntry:
    """InvertedIndexEntry — maps fuzzy memory to exact source."""

    def test_default_values(self):
        entry = InvertedIndexEntry()
        assert entry.fuzzy_id == ""
        assert entry.exact_type == ""
        assert entry.exact_id == ""
        assert entry.relevance == 1.0

    def test_custom_values(self):
        entry = InvertedIndexEntry(
            fuzzy_id="fuzzy_abc",
            exact_type="memory_turn",
            exact_id="turn_42",
            relevance=0.85,
        )
        assert entry.fuzzy_id == "fuzzy_abc"
        assert entry.exact_type == "memory_turn"
        assert entry.exact_id == "turn_42"
        assert entry.relevance == 0.85

    def test_to_dict(self):
        entry = InvertedIndexEntry(
            fuzzy_id="fuzzy_xyz",
            exact_type="wiki_page",
            exact_id="wiki_001",
            relevance=0.95,
        )
        d = entry.to_dict()
        assert d["fuzzy_id"] == "fuzzy_xyz"
        assert d["exact_type"] == "wiki_page"
        assert d["exact_id"] == "wiki_001"
        assert d["relevance"] == 0.95

    def test_to_dict_defaults(self):
        entry = InvertedIndexEntry()
        d = entry.to_dict()
        assert d["fuzzy_id"] == ""
        assert d["exact_type"] == ""
        assert d["exact_id"] == ""
        assert d["relevance"] == 1.0

    def test_roundtrip_reconstruct_from_dict(self):
        entry = InvertedIndexEntry(
            fuzzy_id="f1",
            exact_type="memory_entry",
            exact_id="e1",
            relevance=0.7,
        )
        d = entry.to_dict()
        reconstructed = InvertedIndexEntry(
            fuzzy_id=d["fuzzy_id"],
            exact_type=d["exact_type"],
            exact_id=d["exact_id"],
            relevance=d["relevance"],
        )
        assert reconstructed.fuzzy_id == entry.fuzzy_id
        assert reconstructed.exact_type == entry.exact_type
        assert reconstructed.exact_id == entry.exact_id
        assert reconstructed.relevance == entry.relevance
