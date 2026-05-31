"""单元测试: MemoryEntryStore"""

import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone

import pytest

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from animetta.memory.models.memory_entry import MemoryEntry, MemoryRelation, RelationType
from animetta.memory.storage.memory_entry_store import MemoryEntryStore


@pytest.fixture
def store():
    """创建内存 SQLite MemoryEntryStore."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(MemoryEntryStore.ddl())
    s = MemoryEntryStore(conn)
    yield s
    conn.close()


def make_entry(space_id: str = "test-space", memory: str = "test fact") -> MemoryEntry:
    return MemoryEntry(
        id=str(uuid.uuid4()),
        memory=memory,
        space_id=space_id,
        version=1,
        is_latest=True,
        is_static=False,
        is_forgotten=False,
        confidence=1.0,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


class TestMemoryEntryCRUD:
    """测试 MemoryEntry 基本 CRUD."""

    def test_create_and_get(self, store):
        entry = make_entry()
        eid = store.create(entry)
        assert eid == entry.id

        fetched = store.get(eid)
        assert fetched is not None
        assert fetched.id == eid
        assert fetched.memory == "test fact"
        assert fetched.space_id == "test-space"
        assert fetched.version == 1
        assert fetched.is_latest is True

    def test_get_not_found(self, store):
        assert store.get("nonexistent") is None

    def test_update(self, store):
        entry = make_entry(memory="original fact")
        eid = store.create(entry)

        entry.memory = "updated fact"
        entry.version = 2
        ok = store.update(entry)
        assert ok is True

        fetched = store.get(eid)
        assert fetched.memory == "updated fact"
        assert fetched.version == 2

    def test_delete(self, store):
        entry = make_entry()
        eid = store.create(entry)
        assert store.get(eid) is not None

        ok = store.delete(eid)
        assert ok is True
        assert store.get(eid) is None

    def test_search_by_space(self, store):
        s1 = make_entry(space_id="space-a", memory="likes TypeScript")
        s2 = make_entry(space_id="space-a", memory="uses Vim")
        s3 = make_entry(space_id="space-b", memory="unrelated")
        store.create(s1)
        store.create(s2)
        store.create(s3)

        results = store.search_by_space("space-a")
        assert len(results) == 2
        assert all(r.space_id == "space-a" for r in results)

        filtered = store.search_by_space("space-a", query="TypeScript")
        assert len(filtered) == 1
        assert filtered[0].memory == "likes TypeScript"

    def test_get_latest_by_memory(self, store):
        e1 = make_entry(memory="likes Python")
        e1_id = store.create(e1)

        # Simulate an update: new version
        e2 = make_entry(memory="likes Python")
        e2.version = 2
        e2.parent_memory_id = e1_id
        e2.root_memory_id = e1_id
        store.create_new_version(e2, e1_id)

        latest = store.get_latest_by_memory("likes Python", "test-space")
        assert latest is not None
        assert latest.version == 2
        assert latest.is_latest is True

        old = store.get(e1_id)
        assert old.is_latest is False


class TestVersionChain:
    """测试版本链."""

    def test_create_new_version(self, store):
        v1 = make_entry(memory="likes dogs")
        v1_id = store.create(v1)

        v2 = make_entry(memory="likes dogs")
        v2.version = 2
        store.create_new_version(v2, v1_id)

        # old should not be latest
        old = store.get(v1_id)
        assert old.is_latest is False

        # new should be latest
        latest = store.get_latest_by_memory("likes dogs", "test-space")
        assert latest is not None
        assert latest.version == 2
        assert latest.parent_memory_id == v1_id
        assert latest.root_memory_id == v1_id

    def test_version_chain(self, store):
        v1 = make_entry(memory="prefers coffee")
        v1_id = store.create(v1)

        v2 = make_entry(memory="prefers coffee")
        v2.version = 2
        store.create_new_version(v2, v1_id)

        v3 = make_entry(memory="prefers coffee")
        v3.version = 3
        store.create_new_version(v3, v2.id)  # v2.id was set by create()

        chain = store.get_version_chain(v1_id)
        assert len(chain) == 3
        assert [e.version for e in chain] == [1, 2, 3]


class TestExpire:
    """测试过期清理."""

    def test_expire_old(self, store):
        from datetime import timedelta

        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        e1 = make_entry(memory="will expire")
        e1.forget_after = past
        store.create(e1)

        e2 = make_entry(memory="will not expire")
        e2.forget_after = future
        store.create(e2)

        count = store.expire_old()
        assert count >= 1

        assert store.get(e1.id).is_forgotten is True
        assert store.get(e2.id).is_forgotten is False


class TestRelation:
    """测试记忆关系."""

    def test_add_and_get_relations(self, store):
        e1 = make_entry(memory="likes dogs")
        e2 = make_entry(memory="likes cats")
        e3 = make_entry(memory="loves all pets")
        e1_id = store.create(e1)
        e2_id = store.create(e2)
        e3_id = store.create(e3)

        store.add_relation(MemoryRelation(
            source_id=e3_id, target_id=e1_id, relation=RelationType.EXTENDS,
        ))
        store.add_relation(MemoryRelation(
            source_id=e3_id, target_id=e2_id, relation=RelationType.EXTENDS,
        ))

        rels = store.get_relations(e3_id)
        assert len(rels) == 2
        assert all(r.relation == RelationType.EXTENDS for r in rels)

    def test_get_related_entries(self, store):
        e1 = make_entry(memory="likes dogs")
        e2 = make_entry(memory="likes cats")
        parent_id = store.create(e1)
        child_id = store.create(e2)

        store.add_relation(MemoryRelation(
            source_id=child_id, target_id=parent_id, relation=RelationType.DERIVES,
        ))

        related = store.get_related_entries(child_id)
        assert len(related) == 1
        entry, rel = related[0]
        assert entry.id == parent_id
        assert rel == RelationType.DERIVES


class TestCountAndGetAll:
    """测试统计和批量查询."""

    def test_get_all_latest(self, store):
        for i in range(5):
            store.create(make_entry(memory=f"fact {i}"))

        all_entries = store.get_all_latest("test-space")
        assert len(all_entries) == 5

    def test_count_by_space(self, store):
        store.create(make_entry(space_id="a"))
        store.create(make_entry(space_id="a"))
        store.create(make_entry(space_id="b"))

        assert store.count_by_space("a") == 2
        assert store.count_by_space("b") == 1
