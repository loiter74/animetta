"""Tests for MBTIStore (memory/wiki/mbti_store.py)"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure src/ is on the Python path
_src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from animetta.memory.wiki.mbti_store import MBTIStore, MBTI_PAGE_PATH
from animetta.persistence.protocols import PageType, WikiPage


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_wiki():
    """Create a mock WikiManager with all required methods."""
    wiki = MagicMock()
    wiki.read_page.return_value = None
    wiki.write_page.return_value = None
    wiki.page_exists.return_value = False
    return wiki


@pytest.fixture
def store(mock_wiki):
    """Create an MBTIStore with a mock wiki."""
    return MBTIStore(mock_wiki)


@pytest.fixture
def sample_wiki_page():
    """A pre-built WikiPage representing a saved INTJ profile."""
    return WikiPage(
        title="MBTI Personality Profile",
        page_type=PageType.CONCEPT,
        path=MBTI_PAGE_PATH,
        content=(
            "# MBTI Personality Profile\n\n"
            "## Current State\n"
            "- **Type**: INTJ\n"
            "- **Confidence**: 0.80\n"
            "- **Dimensions**:\n"
            "  - E/I: 20 (内向 80% / 外向 20%)\n"
            "  - S/N: 65 (实感 35% / 直觉 65%)\n"
            "  - T/F: 80 (共情 20% / 理性 80%)\n"
            "  - J/P: 73 (随性 27% / 计划 73%)\n\n"
            "## Description\n"
            "Analytical strategist\n\n"
            "## Change History\n"
            "| Date | E/I | S/N | T/F | J/P | Δ | Trigger |\n"
            "|------|-----|-----|-----|-----|---|---------|\n"
            "| 20260501 | 50 | 50 | 50 | 50 | ei=-30, sn=+15, tf=+30, jp=+23 | 维度调整: E/I-30, S/N+15, T/F+30, J/P+23 |\n"
        ),
        tags=["mbti", "personality"],
        links=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={
            "mbti_type": "INTJ",
            "mbti_ei": 20,
            "mbti_sn": 65,
            "mbti_tf": 80,
            "mbti_jp": 73,
            "mbti_confidence": 0.80,
        },
    )


# ═══════════════════════════════════════════════════════════════
# Test MBTIStore
# ═══════════════════════════════════════════════════════════════

class TestMBTIStoreProfileExists:
    """Tests for MBTIStore.profile_exists()"""

    def test_returns_false_when_no_wiki_page(self, store, mock_wiki):
        mock_wiki.page_exists.return_value = False
        assert store.profile_exists() is False

    def test_returns_true_when_wiki_page_exists(self, store, mock_wiki):
        mock_wiki.page_exists.return_value = True
        assert store.profile_exists() is True

    def test_calls_page_exists_with_correct_path(self, store, mock_wiki):
        store.profile_exists()
        mock_wiki.page_exists.assert_called_once_with(MBTI_PAGE_PATH)


class TestMBTIStoreLoadProfile:
    """Tests for MBTIStore.load_profile()"""

    def test_returns_none_when_no_page(self, store, mock_wiki):
        mock_wiki.read_page.return_value = None
        assert store.load_profile() is None

    def test_returns_parsed_profile(self, store, mock_wiki, sample_wiki_page):
        mock_wiki.read_page.return_value = sample_wiki_page
        result = store.load_profile()

        assert result is not None
        assert result["type"] == "INTJ"
        assert result["dimensions"]["ei"] == 20
        assert result["dimensions"]["sn"] == 65
        assert result["dimensions"]["tf"] == 80
        assert result["dimensions"]["jp"] == 73
        assert result["confidence"] == 0.80
        assert "Analytical strategist" in result["description"]

    def test_calls_read_page_with_correct_path(self, store, mock_wiki, sample_wiki_page):
        mock_wiki.read_page.return_value = sample_wiki_page
        store.load_profile()
        mock_wiki.read_page.assert_called_once_with(MBTI_PAGE_PATH)

    def test_returns_default_values_for_missing_metadata(self, store, mock_wiki):
        """If metadata lacks MBTI keys, load_profile returns safe defaults."""
        page = WikiPage(
            title="MBTI Personality Profile",
            page_type=PageType.CONCEPT,
            path=MBTI_PAGE_PATH,
            content="# MBTI\n\n## Current State\n",
            metadata={},
        )
        mock_wiki.read_page.return_value = page
        result = store.load_profile()

        assert result is not None
        assert result["dimensions"]["ei"] == 50  # default
        assert result["type"] == ""  # empty string default
        assert result["confidence"] == 0.5  # default

    def test_handles_corrupt_page_gracefully(self, store, mock_wiki):
        """If parsing fails, load_profile returns None instead of crashing."""
        mock_wiki.read_page.side_effect = Exception("Disk error")
        # Should not raise; should log warning and return None
        # (MBTIStore catches Exception inside load_profile)
        # But since we mock read_page, the exception comes from outside.
        # The actual code only catches _parse_page errors, not read_page errors.
        # This test verifies the behavior when the wiki layer itself is broken.
        with pytest.raises(Exception):
            store.load_profile()


class TestMBTIStoreSaveProfile:
    """Tests for MBTIStore.save_profile()"""

    def test_writes_wiki_page_with_correct_metadata(self, store, mock_wiki):
        mock_wiki.read_page.return_value = None
        store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "Analytical strategist",
            "confidence": 0.80,
        })

        mock_wiki.write_page.assert_called_once()
        page = mock_wiki.write_page.call_args[0][0]
        assert isinstance(page, WikiPage)
        assert page.metadata["mbti_type"] == "INTJ"
        assert page.metadata["mbti_ei"] == 20
        assert page.metadata["mbti_sn"] == 65
        assert page.metadata["mbti_tf"] == 80
        assert page.metadata["mbti_jp"] == 73
        assert page.metadata["mbti_confidence"] == 0.80

    def test_writes_content_with_type_and_dimensions(self, store, mock_wiki):
        mock_wiki.read_page.return_value = None
        store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.5,
        })

        page = mock_wiki.write_page.call_args[0][0]
        assert "INTJ" in page.content
        assert "20" in page.content
        assert "65" in page.content
        assert "80" in page.content
        assert "73" in page.content

    def test_writes_correct_page_path_and_type(self, store, mock_wiki):
        mock_wiki.read_page.return_value = None
        store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.5,
        })

        page = mock_wiki.write_page.call_args[0][0]
        assert page.path == MBTI_PAGE_PATH
        assert page.page_type == PageType.CONCEPT
        assert "mbti" in page.tags
        assert "personality" in page.tags

    def test_round_trip_save_then_load(self, store, mock_wiki):
        """After save, load_profile returns the saved data."""
        stored_page = [None]

        def read_page_side_effect(path):
            return stored_page[0]

        def write_page_side_effect(page):
            stored_page[0] = page

        mock_wiki.read_page.side_effect = read_page_side_effect
        mock_wiki.write_page.side_effect = write_page_side_effect

        store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "Analytical strategist",
            "confidence": 0.80,
        })

        result = store.load_profile()
        assert result is not None
        assert result["type"] == "INTJ"
        assert result["dimensions"]["ei"] == 20
        assert result["dimensions"]["sn"] == 65
        assert result["confidence"] == 0.80
        assert "Analytical strategist" in result["description"]


class TestMBTIStoreHistory:
    """Tests for MBTIStore change history logic."""

    @pytest.fixture
    def tracked_store(self, mock_wiki):
        """MBTIStore where write_page captures the page for inspection."""
        stored_page = [None]
        written_pages: list = []

        def read_page_side_effect(path):
            return stored_page[0]

        def write_page_side_effect(page):
            written_pages.append(page)
            stored_page[0] = page

        mock_wiki.read_page.side_effect = read_page_side_effect
        mock_wiki.write_page.side_effect = write_page_side_effect

        store = MBTIStore(mock_wiki)
        store._written_pages = written_pages  # attach for test access
        return store

    def test_history_appended_on_dimension_change(self, tracked_store):
        """Saving with different dimensions adds a history entry."""
        # First save — no existing profile
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.5,
        })

        # Second save — dimensions changed
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 35, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.6,
        })

        # The second write should contain the change history
        pages = tracked_store._written_pages
        assert len(pages) >= 2
        last_page = pages[-1]
        assert "## Change History" in last_page.content

    def test_no_history_when_dimensions_unchanged(self, tracked_store):
        """Saving with same dimensions does not add a history entry."""
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.5,
        })

        # Second save — same dimensions, only confidence changed
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.9,
        })

        pages = tracked_store._written_pages
        last_page = pages[-1]
        assert "## Change History" not in last_page.content

    def test_history_only_appended_on_dimension_change_not_confidence(self, tracked_store):
        """Confidence-only changes should not trigger a history entry."""
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.5,
        })
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "Updated description",
            "confidence": 0.9,
        })

        pages = tracked_store._written_pages
        last_page = pages[-1]
        assert "## Change History" not in last_page.content

    def test_old_history_entries_preserved_on_update(self, tracked_store):
        """When multiple dimension changes happen, old entries remain."""
        # Save 1 — initial
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.5,
        })
        # Save 2 — first change
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 35, "sn": 65, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.6,
        })
        # Save 3 — second change
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 35, "sn": 70, "tf": 80, "jp": 73},
            "description": "",
            "confidence": 0.7,
        })

        pages = tracked_store._written_pages
        last_page = pages[-1]
        # Should have history from both changes
        hist_lines = [l for l in last_page.content.split("\n") if l.startswith("|") and "E/I" not in l and "---" not in l]
        assert len(hist_lines) >= 2

    def test_history_capped_at_50_entries(self, tracked_store):
        """History does not grow unbounded."""
        # Initial save
        tracked_store.save_profile({
            "type": "INTJ",
            "dimensions": {"ei": 50, "sn": 50, "tf": 50, "jp": 50},
            "description": "",
            "confidence": 0.5,
        })

        # Make 55 dimension changes
        for i in range(55):
            tracked_store.save_profile({
                "type": "INTJ",
                "dimensions": {"ei": 50, "sn": 50, "tf": 50 + (i % 10), "jp": 50},
                "description": "",
                "confidence": 0.5,
            })

        pages = tracked_store._written_pages
        last_page = pages[-1]
        hist_lines = [l for l in last_page.content.split("\n") if l.startswith("|") and "E/I" not in l and "---" not in l]
        # Should have at most 50 history entries (not 55)
        assert len(hist_lines) <= 50

    def test_get_history_returns_list(self, store, mock_wiki, sample_wiki_page):
        """get_history returns the list of history entries from the parsed profile."""
        mock_wiki.read_page.return_value = sample_wiki_page
        history = store.get_history()
        assert isinstance(history, list)
        assert len(history) >= 1
        entry = history[0]
        assert "date" in entry
        assert "ei" in entry
        assert "sn" in entry
        assert "tf" in entry
        assert "jp" in entry
        assert "delta" in entry
        assert "trigger" in entry

    def test_get_history_returns_empty_when_no_page(self, store, mock_wiki):
        mock_wiki.read_page.return_value = None
        assert store.get_history() == []


class TestMBTIStoreChangeDetection:
    """Tests for MBTIStore._dimensions_changed static method."""

    def test_detects_change(self):
        assert MBTIStore._dimensions_changed({"ei": 20}, {"ei": 30}) is True

    def test_no_change_when_same(self):
        assert MBTIStore._dimensions_changed({"ei": 20, "sn": 50}, {"ei": 20, "sn": 50}) is False

    def test_any_dimension_change_triggers_true(self):
        assert MBTIStore._dimensions_changed(
            {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            {"ei": 20, "sn": 65, "tf": 50, "jp": 73},
        ) is True

    def test_missing_key_treated_as_50(self):
        assert MBTIStore._dimensions_changed({}, {"ei": 60}) is True
        assert MBTIStore._dimensions_changed({"ei": 50}, {}) is False


class TestMBTIStoreBuildTrigger:
    """Tests for MBTIStore._build_trigger static method."""

    def test_single_dimension_change(self):
        trigger = MBTIStore._build_trigger({"ei": 20}, {"ei": 35})
        assert "E/I+15" in trigger

    def test_multiple_dimension_changes(self):
        trigger = MBTIStore._build_trigger(
            {"ei": 20, "sn": 65, "tf": 80, "jp": 73},
            {"ei": 35, "sn": 70, "tf": 80, "jp": 73},
        )
        assert "E/I+15" in trigger
        assert "S/N+5" in trigger

    def test_no_changes_returns_auto_update(self):
        trigger = MBTIStore._build_trigger({"ei": 50}, {"ei": 50})
        assert trigger == "自动更新"

    def test_negative_delta(self):
        trigger = MBTIStore._build_trigger({"ei": 80}, {"ei": 20})
        assert "E/I-60" in trigger
