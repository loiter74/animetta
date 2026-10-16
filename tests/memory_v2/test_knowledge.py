from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from animetta.memory.v2.context import MemoryContext
from animetta.memory.v2.system import LivingMemorySystem
from animetta.orchestration.server.websocket import WebSocketServer

TEXT = "张三住在杭州，喜欢咖啡。"
BATCH = {
    "entities": [
        {"key": "p", "name": "张三", "type": "person"},
        {"key": "c", "name": "杭州", "type": "place"},
        {"key": "v", "name": "咖啡", "type": "concept"},
    ],
    "facts": [
        {
            "subject": "p",
            "predicate": "居住地",
            "object": "c",
            "role": "user",
            "evidence": TEXT,
            "confidence": 0.95,
        },
        {
            "subject": "p",
            "predicate": "喜欢",
            "object": "v",
            "role": "user",
            "evidence": TEXT,
            "confidence": 0.9,
        },
    ],
}


@pytest.fixture
async def system(tmp_path):
    llm = AsyncMock(return_value=json.dumps(BATCH, ensure_ascii=False))
    memory = LivingMemorySystem(str(tmp_path / "knowledge.sqlite"), llm_call=llm)
    await memory.initialize()
    yield memory, llm
    await memory.shutdown()


async def encode(memory, text=TEXT, actor="local:owner"):
    return await memory.encode(
        text, "记住了。", context=MemoryContext(actor_id=actor, channel="local")
    )


async def test_one_turn_extracts_independent_facts_and_survives_reopen(system):
    memory, llm = system
    source = await encode(memory)
    pages = await memory.list_memories()
    facts = [item for item in pages["items"] if item["page_type"] == "fact"]
    entities = [item for item in pages["items"] if item["knowledge"].get("kind") == "entity"]
    assert len(facts) == 2
    assert len(entities) == 3
    assert {item["knowledge"]["predicate"] for item in facts} == {"居住地", "喜欢"}
    ids = {item["id"] for item in entities}
    for fact in facts:
        assert fact["knowledge"]["subject_id"] in ids
        assert fact["knowledge"]["object_id"] in ids
        assert fact["source_ids"] == [source.id]
        assert fact["knowledge"]["evidence"][0]["quote"] == TEXT
        assert fact["scope"] == "viewer" and fact["visibility"] == "private"
    assert pages["knowledge"]["pending_sources"] == 0
    assert json.loads(llm.call_args.args[1])["messages"]["user"] == TEXT
    await memory.shutdown()
    reopened = LivingMemorySystem(memory.store.db_path)
    await reopened.initialize()
    try:
        restored = await reopened.list_memories()
        assert {item["id"] for item in restored["items"]} == {item["id"] for item in pages["items"]}
        assert restored["knowledge"]["facts"] == 2
    finally:
        await reopened.shutdown()


async def test_aliases_merge_facts_and_evidence_without_crossing_viewer_boundary(system):
    memory, llm = system
    first = await encode(memory)
    alias_batch = copy.deepcopy(BATCH)
    alias_batch["entities"][0].update(name="阿三", aliases=["张三"])
    llm.return_value = json.dumps(alias_batch, ensure_ascii=False)
    second = await encode(memory)
    page = await memory.list_memories()
    facts = [item for item in page["items"] if item["page_type"] == "fact"]
    assert page["knowledge"]["entities"] == 3
    assert len(facts) == 2
    assert set(facts[0]["source_ids"]) == {first.id, second.id}
    await encode(memory, actor="bilibili:another-viewer")
    page = await memory.list_memories()
    assert page["knowledge"]["entities"] == 6
    assert page["knowledge"]["facts"] == 4


@pytest.mark.parametrize("failure", ["bad_json", "unknown_entity", "invented_evidence"])
async def test_invalid_extraction_preserves_source_and_organize_retries(system, failure):
    memory, llm = system
    invalid = copy.deepcopy(BATCH)
    if failure == "unknown_entity":
        invalid["facts"][0]["subject"] = "missing"
    elif failure == "invented_evidence":
        invalid["facts"][0]["evidence"] = "没有说过的话"
    llm.return_value = "not json" if failure == "bad_json" else json.dumps(invalid)
    source = await encode(memory)
    assert await memory.store.count_active() == 1
    assert (await memory.store.get(source.id)).knowledge["status"] == "pending"
    with pytest.raises(ValueError):
        await memory.organize_knowledge()
    llm.return_value = json.dumps(BATCH)
    stats = await memory.organize_knowledge()
    assert stats["sources_processed"] == 1
    assert stats["facts_created"] == 2 and stats["pending_sources"] == 0
    calls = llm.await_count
    assert (await memory.organize_knowledge())["sources_processed"] == 0
    assert llm.await_count == calls


async def test_extraction_commit_rolls_back_all_nodes_on_failure(system, monkeypatch):
    memory, _ = system
    original = memory.store._create

    async def fail_on_fact(atom):
        if atom.knowledge.get("kind") == "fact":
            raise OSError("storage write interrupted")
        return await original(atom)

    monkeypatch.setattr(memory.store, "_create", fail_on_fact)
    source = await encode(memory)
    assert await memory.store.count_active() == 1
    assert (await memory.store.get(source.id)).knowledge["status"] == "pending"
    monkeypatch.setattr(memory.store, "_create", original)
    assert (await memory.organize_knowledge())["entities_created"] == 3


async def test_forgetting_source_retracts_only_unsupported_knowledge(system):
    memory, _ = system
    first, second = await encode(memory), await encode(memory)
    await memory.forget_memory(first.id)
    page = await memory.list_memories()
    assert page["knowledge"]["facts"] == 2
    for item in page["items"]:
        assert first.id not in item["source_ids"]
    await memory.forget_memory(second.id)
    page = await memory.list_memories()
    assert page["knowledge"]["entities"] == page["knowledge"]["facts"] == 0


async def test_forget_is_not_undone_by_organizing_old_sources(system):
    memory, _ = system
    await encode(memory)
    page = await memory.list_memories()
    person = next(
        item for item in page["items"] if item["page_type"] == "entity" and item["title"] == "张三"
    )
    await memory.forget_memory(person["id"])
    await memory.organize_knowledge()
    assert (await memory.list_memories())["knowledge"]["facts"] == 0
    fresh = await encode(memory)
    facts = [
        item for item in (await memory.list_memories())["items"] if item["page_type"] == "fact"
    ]
    assert len(facts) == 2
    assert all(item["source_ids"] == [fresh.id] for item in facts)


async def test_pagination_retains_all_graph_endpoints(system):
    memory, _ = system
    await encode(memory)
    items, cursor = [], None
    while True:
        page = await memory.list_memories(limit=2, cursor=cursor)
        items.extend(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(items) == 6
    assert len({item["id"] for item in items}) == 6


async def test_missing_extractor_cannot_report_successful_organization(tmp_path):
    memory = LivingMemorySystem(str(tmp_path / "no-extractor.sqlite"))
    await memory.initialize()
    try:
        await encode(memory)
        with pytest.raises(RuntimeError, match="provider is unavailable"):
            await memory.organize_knowledge()
    finally:
        await memory.shutdown()


async def test_runtime_extraction_borrows_history_neutral_real_provider():
    engine = SimpleNamespace(
        chat_messages=AsyncMock(return_value='{"entities":[],"facts":[]}'),
        chat=AsyncMock(),
        is_mock_provider=False,
    )
    server = WebSocketServer.__new__(WebSocketServer)
    server.provider_pool = SimpleNamespace(get_context=lambda: {"llm_engine": engine})
    await server._memory_llm_call("extract", "source")
    assert engine.chat_messages.call_args.args[0] == [
        {"role": "system", "content": "extract"},
        {"role": "user", "content": "source"},
    ]
    engine.chat.assert_not_called()
    engine.is_mock_provider = True
    with pytest.raises(RuntimeError, match="real LLM"):
        await server._memory_llm_call("extract", "source")


async def test_no_assertions_produces_no_invented_graph_nodes(system):
    memory, llm = system
    llm.return_value = '{"entities":[],"facts":[]}'
    source = await encode(memory, text="你好，现在方便聊聊吗？")
    assert await memory.store.count_active() == 1
    assert (await memory.store.get(source.id)).knowledge["status"] == "complete"
    assert (await memory.organize_knowledge())["facts_created"] == 0


async def test_summary_edits_cannot_silently_change_a_structured_fact(system):
    memory, _ = system
    await encode(memory)
    fact = next(
        item for item in (await memory.list_memories())["items"] if item["page_type"] == "fact"
    )
    with pytest.raises(ValueError, match="新的陈述"):
        await memory.change_memory(fact["id"], summary="随意改写一条事实")
    assert (await memory.get_memory(fact["id"]))["knowledge"] == fact["knowledge"]
