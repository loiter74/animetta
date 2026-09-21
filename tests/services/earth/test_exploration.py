"""Behavioral tests with real graph checkpoints and injected external boundaries."""

import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from animetta.orchestration.graph.earth_graph import build_earth_graph
from animetta.services.earth import Candidate, EarthError, ExplorationRules
from animetta.services.earth.exploration import ExplorationService
from animetta.services.earth.photon import PhotonSearch
from animetta.tools.earth import get_earth_tools


def candidate(name: str = "杭州") -> Candidate:
    return Candidate(
        id="relation:1",
        name=name,
        longitude=120.15,
        latitude=30.28,
        height=10000,
        source={"name": "test source", "url": "https://example.org/1", "attribution": "test"},
    )


async def ready_state(service: ExplorationService, *, voice: bool = False) -> dict:
    state = await service.apply(
        {},
        {
            "operation": "open",
            "conversation_id": "test",
            "control_revision": 0,
            "voice_enabled": voice,
        },
    )
    state = await service.apply(state, {"operation": "text", "text": "杭州", "control_revision": 1})
    state = await service.apply(
        state, {"operation": "select", "candidate_id": "relation:1", "control_revision": 2}
    )
    return await service.apply(
        state,
        {
            "operation": "result",
            "action_id": state["action_id"],
            "status": "ready",
            "view_revision": 1,
            "control_revision": 2,
        },
    )


async def test_photon_real_response_mapping_and_rate_limit() -> None:
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {"coordinates": [120.15, 30.28]},
                        "properties": {
                            "name": "杭州",
                            "osm_type": "R",
                            "osm_id": 1,
                            "extent": [119, 31, 121, 29],
                        },
                    }
                ]
            },
        )

    provider = PhotonSearch(transport=httpx.MockTransport(handle))
    results = await provider.search("杭州")
    assert results[0].bounds == (119, 29, 121, 31)
    assert results[0].source.url == "https://www.openstreetmap.org/relation/1"
    assert requests[0].url.params["q"] == "杭州"
    with pytest.raises(EarthError, match="查询过于频繁"):
        await provider.search("上海")
    assert len(requests) == 1


async def test_graph_interrupts_selection_and_navigation_receipts() -> None:
    search = SimpleNamespace(search=AsyncMock(return_value=[candidate()]))
    graph = build_earth_graph(InMemorySaver())
    service = ExplorationService(search, clock=lambda: 100)
    config = {"configurable": {"thread_id": "earth-test", "earth_service": service}}
    await graph.ainvoke(
        {
            "snapshot": {},
            "event": {"operation": "open", "conversation_id": "test", "control_revision": 0},
        },
        config,
    )
    await graph.ainvoke(
        Command(resume={"operation": "text", "text": "杭州", "control_revision": 1}), config
    )
    saved = await graph.aget_state(config)
    assert saved.tasks[0].interrupts
    assert saved.values["snapshot"]["phase"] == "waiting_selection"
    assert not saved.values["snapshot"]["outbox"]
    await graph.ainvoke(
        Command(
            resume={"operation": "select", "candidate_id": "relation:1", "control_revision": 2}
        ),
        config,
    )
    state = (await graph.aget_state(config)).values["snapshot"]
    assert state["phase"] == "moving"
    assert state["outbox"][0]["payload"]["target"]["longitude"] == 120.15
    await graph.ainvoke(
        Command(
            resume={
                "operation": "result",
                "action_id": state["action_id"],
                "status": "arrived",
                "view_revision": 1,
                "control_revision": 2,
            }
        ),
        config,
    )
    assert (await graph.aget_state(config)).values["snapshot"]["phase"] == "moving"
    search.search.assert_awaited_once_with("杭州")


async def test_playback_requires_started_and_ended_then_five_seconds() -> None:
    now = [100.0]
    service = ExplorationService(
        SimpleNamespace(search=AsyncMock(return_value=[candidate()])),
        clock=lambda: now[0],
        tts=SimpleNamespace(synthesize=AsyncMock(return_value=b"audio"), audio_format="wav"),
    )
    state = await ready_state(service, voice=True)
    assert state["phase"] == "awaiting_playback" and state["feedback_deadline"] is None
    task_id = state["task_id"]
    event = {"operation": "playback_ended", "task_id": task_id, "control_revision": 2}
    state = await service.apply(state, event)
    assert state["phase"] == "awaiting_playback"
    state = await service.apply(state, {**event, "operation": "playback_started"})
    state = await service.apply(state, event)
    assert state["feedback_deadline"] == 105
    now[0] = 104.9
    assert (await service.apply(state, {"operation": "tick", "control_revision": 2}))[
        "phase"
    ] == "feedback"
    now[0] = 105
    state = await service.apply(state, {"operation": "tick", "control_revision": 2})
    assert state["phase"] == "moving" and state["steps"] == 2
    duplicate = await service.apply(state, event)
    assert duplicate["phase"] == "moving" and duplicate["feedback_deadline"] is None


def test_domain_limits_and_clock_regression() -> None:
    rules = ExplorationRules()
    for selected, steps, now, phase in [
        (False, 0, 10, "feedback"),
        (True, 3, 10, "feedback"),
        (True, 1, 60, "feedback"),
        (True, 1, -1, "feedback"),
        (True, 1, 10, "paused"),
    ]:
        assert not rules.can_continue(
            selected=selected, steps=steps, started=0, now=now, phase=phase
        )
    assert rules.can_continue(selected=True, steps=2, started=0, now=59, phase="feedback")


async def test_failed_voice_text_and_private_asr(monkeypatch) -> None:
    async def transcribe(audio_data: bytes, *, audio_format: str) -> str:
        assert audio_data == b"normalized-wav" and audio_format == "wav"
        return "杭州"

    asr = SimpleNamespace(transcribe=transcribe)
    normalizer = AsyncMock(return_value=b"normalized-wav")
    monkeypatch.setattr("animetta.services.earth.exploration.normalize_asr_audio", normalizer)
    search = SimpleNamespace(search=AsyncMock(return_value=[candidate()]))
    tts = SimpleNamespace(synthesize=AsyncMock(side_effect=RuntimeError()), audio_format="wav")
    service = ExplorationService(search, clock=lambda: 100, tts=tts, asr=asr)
    state = await ready_state(service, voice=True)
    assert state["phase"] == "reading" and state["feedback_deadline"] == 107
    assert state["outbox"][0]["payload"]["status"] == "text_only"
    state = await service.apply(
        state,
        {
            "operation": "audio",
            "audio_data": base64.b64encode(b"wav").decode(),
            "format": "wav",
            "control_revision": 3,
        },
    )
    assert state["transcript"][-2] == {"role": "user", "text": "杭州"}
    normalizer.assert_awaited_once_with(b"wav", "wav")


async def test_tools_refuse_unbound_public_invocation() -> None:
    for tool in get_earth_tools():
        arguments = (
            {"query": "上海"}
            if tool.name == "earth_search"
            else ({"candidate_id": "relation:1"} if tool.name == "earth_navigate" else {})
        )
        with pytest.raises(EarthError, match="私密探索"):
            await tool.ainvoke(arguments, config={"configurable": {}})


async def test_private_history_neutral_model_query() -> None:
    messages_seen = []

    class LLM:
        async def chat_messages_stream(self, messages):
            messages_seen.append(messages)
            yield '{"query":"杭州"}'

    service = ExplorationService(
        SimpleNamespace(search=AsyncMock(return_value=[candidate()])), clock=lambda: 100, llm=LLM()
    )
    await ready_state(service)
    assert messages_seen[0][-1] == {"role": "user", "content": "杭州"}
    assert all("memory" not in message for message in messages_seen[0])


@pytest.mark.parametrize(
    "text,phase",
    [
        ("等一下", "paused"),
        ("不是青浦", "waiting_input"),
        ("这条路我经常走", "waiting_identification"),
        ("这个地方是干什么的？", "waiting_input"),
    ],
)
async def test_nonsearch_intents_never_query_provider(text, phase) -> None:
    search = SimpleNamespace(search=AsyncMock(return_value=[candidate()]))
    service = ExplorationService(search, clock=lambda: 100)
    state = await ready_state(service)
    search.search.reset_mock()
    state = await service.apply(state, {"operation": "text", "text": text, "control_revision": 3})
    assert state["phase"] == phase
    search.search.assert_not_awaited()
    assert state["feedback_deadline"] is None
    if text.startswith("不是"):
        assert state["selected"] is None and not state["candidates"]


async def test_point_freezes_and_continue_uses_actual_view() -> None:
    service = ExplorationService(
        SimpleNamespace(search=AsyncMock(return_value=[candidate()])), clock=lambda: 100
    )
    state = await ready_state(service)
    view = {"longitude": 120.5, "latitude": 30.7, "height": 2000, "heading": 1.0, "pitch": -0.6}
    state = await service.apply(
        state, {"operation": "context", "view": view, "view_revision": 10, "control_revision": 2}
    )
    state = await service.apply(state, {"operation": "continue", "control_revision": 3})
    assert state["target"]["longitude"] == 120.5 and state["target"]["height"] == 1300
    assert state["target"]["heading"] == 1.0 and state["target"]["pitch"] == -0.6
    assert "2000" in state["navigation_reason"] and "1300" in state["navigation_reason"]
    state = await service.apply(
        state,
        {
            "operation": "select",
            "point": {"longitude": 120.51, "latitude": 30.71},
            "control_revision": 4,
        },
    )
    assert state["phase"] == "waiting_identification" and not state["outbox"]
    assert state["view"] == view and state["feedback_deadline"] is None
    state = await service.apply(state, {"operation": "continue", "control_revision": 5})
    assert state["phase"] == "waiting_identification" and not state["outbox"]


async def test_voice_toggle_applies_after_open() -> None:
    tts = SimpleNamespace(synthesize=AsyncMock(return_value=b"audio"), audio_format="wav")
    service = ExplorationService(
        SimpleNamespace(search=AsyncMock(return_value=[candidate()])), clock=lambda: 100, tts=tts
    )
    state = await ready_state(service)
    tts.synthesize.assert_not_awaited()
    state = await service.apply(
        state, {"operation": "pause", "control_revision": 3, "voice_enabled": True}
    )
    state = await service.apply(state, {"operation": "continue", "control_revision": 4})
    state = await service.apply(
        state,
        {
            "operation": "result",
            "action_id": state["action_id"],
            "status": "ready",
            "view_revision": 2,
            "control_revision": 4,
        },
    )
    assert state["phase"] == "awaiting_playback"
    tts.synthesize.assert_awaited_once()
