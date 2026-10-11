"""Explicit retrieval modes preserve SQLite and expose optional backend failures."""

import builtins
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from animetta.memory.v2.atom import Layer, MemoryAtom
from animetta.memory.v2.store import AtomStore
from animetta.memory.v2.system import LivingMemorySystem
from animetta.runtime.shared_memory import SharedMemoryRuntime


def block_chroma(monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name == "chromadb" or name.startswith("chromadb."):
            raise ImportError("optional backend deliberately absent")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)


async def test_core_fts_persists_versions_without_loading_optional_backend(tmp_path, monkeypatch):
    block_chroma(monkeypatch)
    path = str(tmp_path / "memory.sqlite")
    store = AtomStore(path)
    await store.initialize()
    try:
        await store.create(
            MemoryAtom(
                id="tea", layer=Layer.RAW, content="午饭喝了茉莉茶", occurred_at=datetime.now(UTC)
            )
        )
        await store.create_version("tea", "午饭喝了绿茶", 0.8, (0, 0, 0))
        revision = await store.get_revision()
        await store.process_index_outbox()
        assert [item.id for item in await store.hybrid_search("绿茶")] == ["tea"]
        assert await store.hybrid_search("咖啡") == []  # FTS does not invent semantic synonyms.
    finally:
        await store.close()
    reopened = AtomStore(path)
    await reopened.initialize()
    try:
        restored = await reopened.get("tea")
        assert restored.version == 2
        assert restored.summary == "午饭喝了绿茶"
        assert await reopened.get_revision() == revision
    finally:
        await reopened.close()


async def test_explicit_semantic_missing_dependency_fails_and_closes_sqlite(tmp_path, monkeypatch):
    block_chroma(monkeypatch)
    store = AtomStore(str(tmp_path / "memory.sqlite"), enable_chroma=True)
    with pytest.raises(RuntimeError, match="Semantic memory requires"):
        await store.initialize()
    assert store._conn is None
    assert store._closing


async def test_semantic_index_uses_the_selected_database_directory(tmp_path, monkeypatch):
    import sys

    captured = {}
    collection = SimpleNamespace(query=lambda **kwargs: {"ids": [[]], "distances": [[]]})

    def client(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(get_or_create_collection=lambda **kwargs: collection)

    chroma = ModuleType("chromadb")
    chroma.PersistentClient = client
    settings = ModuleType("chromadb.config")
    settings.Settings = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "chromadb", chroma)
    monkeypatch.setitem(sys.modules, "chromadb.config", settings)
    store = AtomStore(str(tmp_path / "memory.sqlite"), enable_chroma=True)
    await store.initialize()
    try:
        assert Path(captured["path"]) == tmp_path / "chroma_v2"
        assert store._chroma_collection is collection
    finally:
        await store.close()


async def test_semantic_query_failure_is_visible_in_index_health(tmp_path):
    store = AtomStore(str(tmp_path / "memory.sqlite"))
    await store.initialize()

    def unavailable(**kwargs):
        raise ConnectionError("backend unavailable")

    store._chroma_collection = SimpleNamespace(query=unavailable)
    try:
        assert await store.hybrid_search("jasmine") == []
        health = store.get_index_health()
        assert health["degraded"]
        assert health["last_error"] == "semantic_query_failed:ConnectionError"
    finally:
        await store.close()


async def test_shared_core_runtime_reports_fts_without_vector_backend(tmp_path, monkeypatch):
    block_chroma(monkeypatch)
    runtime = SharedMemoryRuntime(tmp_path / "memory.sqlite", worker_interval=0.01)
    await runtime.initialize()
    try:
        assert runtime.system.retrieval_mode == "fts"
        health = await runtime.health()
        assert health["ready"]
        assert health["retrieval_mode"] == "fts"
        assert health["vector_ready"] is False
    finally:
        await runtime.shutdown()


def test_unknown_mode_is_rejected_before_creating_storage():
    with pytest.raises(ValueError, match="retrieval mode"):
        LivingMemorySystem(retrieval_mode="auto")
