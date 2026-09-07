"""Exercise real SQLite transactions and bounded blocking vector operations."""

from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime

import pytest

from animetta.memory.v2.atom import Layer, MemoryAtom
from animetta.memory.v2.store import AtomStore
from animetta.memory.v2.system import LivingMemorySystem
from animetta.orchestration.graph.memory_middleware import MemoryMiddleware


def atom(identifier: str, content: str = "jasmine tea") -> MemoryAtom:
    return MemoryAtom(
        id=identifier, layer=Layer.RAW, content=content, occurred_at=datetime.now(UTC)
    )


@pytest.fixture
async def store(tmp_path):
    instance = AtomStore(str(tmp_path / "atoms.sqlite"), enable_chroma=False)
    await instance.initialize()
    try:
        yield instance
    finally:
        await instance.close()


class BlockingCollection:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0
        self.documents: list[str] = []

    def query(self, **_kwargs):
        self.calls += 1
        self.entered.set()
        assert self.release.wait(5), "test must release vector worker"
        return {"ids": [["a"]], "distances": [[0.0]]}

    def upsert(self, *, documents, **_kwargs):
        self.documents.extend(documents)
        self.query()


async def entered(event: threading.Event) -> None:
    async with asyncio.timeout(2):
        while not event.is_set():
            await asyncio.sleep(0.001)


async def test_concurrent_writes_and_versions_are_atomic(store):
    await asyncio.gather(*(store.create(atom(str(i))) for i in range(20)))
    assert await store.get_revision() == 20
    assert await store.get_index_backlog() == 20
    versions = await asyncio.gather(
        *(store.create_version("0", str(i), 0.7, (0, 0, 0)) for i in range(8))
    )
    assert sorted(item.version for item in versions) == list(range(2, 10))
    assert await store.get_revision() == 28
    async with store._database():
        history = await store._fetchall(
            "SELECT version FROM memory_versions WHERE atom_id='0' ORDER BY version"
        )
        revisions = await store._fetchall(
            "SELECT revision FROM memory_index_outbox ORDER BY revision"
        )
    assert [row[0] for row in history] == list(range(1, 9))
    assert [row[0] for row in revisions] == list(range(1, 29))


async def test_cancelled_transaction_hides_partial_write_and_rolls_back(store, monkeypatch):
    inserted = asyncio.Event()
    release = asyncio.Event()
    original = store._enqueue_index

    async def pause(*args):
        await original(*args)
        inserted.set()
        await release.wait()

    monkeypatch.setattr(store, "_enqueue_index", pause)
    writer = asyncio.create_task(store.create(atom("cancelled")))
    await inserted.wait()
    reader = asyncio.create_task(store.get("cancelled"))
    await asyncio.sleep(0)
    assert not reader.done()
    writer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await writer
    assert await reader is None
    assert await store.get_revision() == 0
    assert await store.get_index_backlog() == 0
    assert await store.search_fts("jasmine") == []


async def test_cancel_after_commit_queued_waits_before_unlocking(store, monkeypatch):
    queued = asyncio.Event()
    release = asyncio.Event()
    connection = store._conn
    original = connection.commit

    async def commit():
        queued.set()
        await release.wait()
        await original()

    monkeypatch.setattr(connection, "commit", commit)
    writer = asyncio.create_task(store.create(atom("committed")))
    await queued.wait()
    writer.cancel()
    await asyncio.sleep(0)
    writer.cancel()
    reader = asyncio.create_task(store.get("committed"))
    await asyncio.sleep(0)
    assert not reader.done()
    assert not writer.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await writer
    assert (await reader).content == "jasmine tea"
    assert await store.get_revision() == 1


async def test_version_history_rolls_back_together_with_new_atom(store, monkeypatch):
    await store.create(atom("version"))

    async def fail(*_args):
        raise ValueError("injected write failure")

    monkeypatch.setattr(store, "_enqueue_index", fail)
    with pytest.raises(ValueError, match="injected"):
        await store.create_version("version", "new summary", 0.9, (1, 0, 0))
    assert (await store.get("version")).version == 1
    assert await store.get_revision() == 1
    async with store._database():
        assert await store._fetchall("SELECT * FROM memory_versions") == []
    assert await store.search_fts("new") == []


async def test_sqlite_worker_does_not_block_event_loop(store):
    blocked = threading.Event()
    release = threading.Event()

    def block():
        blocked.set()
        assert release.wait(5)
        return 1

    await store._conn.create_function("block", 0, block)

    async def query():
        async with store._database():
            return await store._fetchone("SELECT block()")

    task = asyncio.create_task(query())
    try:
        await entered(blocked)
        assert not task.done()
        await asyncio.sleep(0)
    finally:
        release.set()
        assert (await task)[0] == 1


async def test_recall_deadline_and_cancellations_do_not_queue_vector_work(store):
    collection = BlockingCollection()
    store._chroma_collection = collection
    system = LivingMemorySystem()
    system.store = store
    middleware = MemoryMiddleware(system)
    first = asyncio.create_task(middleware.recall_structured("session", "tea"))
    try:
        await entered(collection.entered)
        prompt, metadata = await asyncio.wait_for(first, 1)
        assert prompt == ""
        assert metadata == {"degraded": True, "reason": "deadline_exceeded", "deadline_ms": 150}
        assert not collection.release.is_set()
        for _ in range(5):
            waiter = asyncio.create_task(store._vector_search("tea"))
            await asyncio.sleep(0)
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter
        assert collection.calls == 1
        assert len(store._vector_tasks) == 1
        # SQLite remains available while vector work is outstanding.
        await store.create(atom("during-vector"))
        assert await store.count_active() == 1
    finally:
        collection.release.set()
        await system.shutdown()


@pytest.mark.parametrize("method", ["process_index_outbox", "rebuild_indexes"])
async def test_old_vector_completion_preserves_new_pending_update(store, method):
    await store.create(atom("a", "old text"))
    collection = BlockingCollection()
    store._chroma_collection = collection
    worker = asyncio.create_task(getattr(store, method)())
    try:
        await entered(collection.entered)
        changed = await store.get("a")
        changed.content = "new text"
        await asyncio.wait_for(store.update(changed), 1)
        assert await store.get_index_backlog() == 2
    finally:
        collection.release.set()
        await worker
    assert collection.documents == ["old text"]
    assert await store.get_index_backlog() == 1
    assert (await store.get("a")).index_state == "pending"
    await store.process_index_outbox()
    assert collection.documents == ["old text", "new text"]
    assert await store.get_index_backlog() == 0
    assert (await store.get("a")).index_state == "ready"


async def test_close_waits_for_vector_work_even_when_waiter_cancelled(store):
    collection = BlockingCollection()
    store._chroma_collection = collection
    query = asyncio.create_task(store._vector_search("tea"))
    closing = None
    try:
        await entered(collection.entered)
        query.cancel()
        with pytest.raises(asyncio.CancelledError):
            await query
        closing = asyncio.create_task(store.close())
        await asyncio.sleep(0)
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing
        closing = asyncio.create_task(store.close())
        await asyncio.sleep(0)
        assert not closing.done()
        assert store._conn is not None
        with pytest.raises(RuntimeError, match="unavailable"):
            await store.create(atom("late"))
    finally:
        collection.release.set()
        await store.close()
        if closing is not None:
            await closing
    assert store._conn is None
    assert not store._vector_tasks


async def test_system_shutdown_joins_reconsolidation_before_closing_store(store, monkeypatch):
    system = LivingMemorySystem()
    system.store = store
    await store.create(atom("a"))
    started = asyncio.Event()
    finished = asyncio.Event()

    async def reconsolidate(*_args):
        started.set()
        try:
            await asyncio.Future()
        finally:
            assert store._conn is not None
            finished.set()

    monkeypatch.setattr(system, "_reconsolidate", reconsolidate)
    await system.recall("jasmine")
    await started.wait()
    await system.shutdown()
    assert finished.is_set()
    assert not system._reconsolidation_tasks
    assert store._conn is None
