"""Unit tests: MemoryEntry new fields + archive/search exclusion."""

import os, sys, uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import sqlite3
import pytest
from animetta.memory.models.memory_entry import MemoryEntry
from animetta.memory.storage.memory_entry_store import MemoryEntryStore


@pytest.fixture
def store():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(MemoryEntryStore.ddl())
    s = MemoryEntryStore(conn)
    yield s
    conn.close()


def make_entry(**kwargs) -> MemoryEntry:
    return MemoryEntry(
        id=kwargs.get("id", str(uuid.uuid4())),
        memory=kwargs.get("memory", "test fact"),
        space_id=kwargs.get("space_id", "test"),
        version=kwargs.get("version", 1),
        is_latest=kwargs.get("is_latest", True),
        confidence=kwargs.get("confidence", 0.8),
        emotion_value=kwargs.get("emotion_value", None),
        retrieval_count=kwargs.get("retrieval_count", 0),
        is_archived=kwargs.get("is_archived", False),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc).isoformat()),
        updated_at=kwargs.get("updated_at", datetime.now(timezone.utc).isoformat()),
    )


class TestNewFields:
    def test_emotion_value_persisted(self, store):
        entry = make_entry(emotion_value=0.8)
        store.create(entry)
        fetched = store.get(entry.id)
        assert fetched.emotion_value == 0.8

    def test_retrieval_count_incremented(self, store):
        entry = make_entry(retrieval_count=0)
        store.create(entry)
        store.increment_retrieval(entry.id)
        fetched = store.get(entry.id)
        assert fetched.retrieval_count == 1
        assert fetched.last_accessed_at is not None

    def test_is_archived_default_false(self, store):
        entry = make_entry()
        store.create(entry)
        fetched = store.get(entry.id)
        assert fetched.is_archived is False


class TestArchiveExclusion:
    def test_search_excludes_archived(self, store):
        active = make_entry(memory="active fact", space_id="test")
        archived = make_entry(memory="archived fact", space_id="test", is_archived=True)
        store.create(active)
        store.create(archived)
        # Mark archived in DB directly (create sets is_archived=0)
        store.conn.execute("UPDATE memory_entries SET is_archived=1 WHERE id=?", (archived.id,))
        store.conn.commit()

        results = store.search_by_space("test")
        memories = [r.memory for r in results]
        assert "active fact" in memories
        assert "archived fact" not in memories

    def test_get_all_latest_excludes_archived(self, store):
        active = make_entry(space_id="test")
        archived = make_entry(space_id="test", is_archived=True)
        store.create(active)
        store.create(archived)
        store.conn.execute("UPDATE memory_entries SET is_archived=1 WHERE id=?", (archived.id,))
        store.conn.commit()

        results = store.get_all_latest("test")
        ids = [r.id for r in results]
        assert active.id in ids
        assert archived.id not in ids


class TestMigration:
    def test_migration_does_not_crash_on_existing_db(self, store):
        """_migrate should be idempotent."""
        store._migrate()
        store._migrate()  # second call should not raise
        # Verify columns exist
        rows = store.conn.execute("SELECT * FROM memory_entries LIMIT 0")
        cols = [d[0] for d in rows.description]
        assert "is_archived" in cols
        assert "emotion_value" in cols
        assert "retrieval_count" in cols
