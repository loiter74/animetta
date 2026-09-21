"""Private SID ownership, cancellation, checkpoints and disabled capability tests."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from animetta.orchestration.server.handlers.earth_handlers import EarthHandlers
from animetta.services.earth import Candidate


@pytest.fixture
def handler():
    principal = SimpleNamespace(
        user_id="alice", session_id="login", source="session", password_change_required=False
    )
    security = SimpleNamespace(
        socket_principal=lambda sid: (
            None
            if sid == "anonymous"
            else (
                SimpleNamespace(
                    user_id=None,
                    session_id="live",
                    source="public-live",
                    password_change_required=False,
                )
                if sid == "live"
                else principal
            )
        )
    )
    ctx = SimpleNamespace(llm_engine=None, tts_engine=None, asr_engine=None)
    base = SimpleNamespace(
        get_or_create_context=AsyncMock(return_value=ctx),
        session_manager=SimpleNamespace(
            checkpoint_runtime=None,
            _load_tools_config=AsyncMock(return_value={"config": {"earth": {"enabled": True}}}),
        ),
    )
    result = EarthHandlers(SimpleNamespace(emit=AsyncMock()), base, security)
    result.search = SimpleNamespace(
        search=AsyncMock(
            return_value=[
                Candidate(
                    id="r:1",
                    name="杭州",
                    longitude=120,
                    latitude=30,
                    height=1000,
                    source={"name": "OSM", "url": "https://example.org", "attribution": "OSM"},
                )
            ]
        )
    )
    return result


async def control(handler, operation, sid="a", revision=0, **extra):
    return await handler.control(
        sid,
        {
            "operation": operation,
            "conversation_id": "private",
            "control_revision": revision,
            **extra,
        },
    )


async def test_unauthenticated_public_and_other_tab_refused(handler) -> None:
    for sid in ("anonymous", "live"):
        assert not (await control(handler, "open", sid=sid))["ok"]
    assert (await control(handler, "open"))["ok"]
    assert (await control(handler, "open", sid="b"))["error"]["code"] == "EARTH_OWNED"
    assert (await control(handler, "text", sid="b", text="Shanghai"))["error"][
        "code"
    ] == "EARTH_NOT_OPEN"
    await handler.disconnect("a")


async def test_private_result_and_stale_revisions(handler) -> None:
    await control(handler, "open")
    reply = await control(handler, "text", text="杭州")
    assert reply["ok"] and reply["state"]["control_revision"] == 1
    reply = await control(handler, "select", revision=1, candidate_id="r:1")
    assert reply["state"]["phase"] == "moving"
    assert reply["state"]["selected"]["name"] == "杭州"
    receipt = {
        "conversation_id": "private",
        "control_revision": 1,
        "view_revision": 1,
        "action_id": reply["state"]["action_id"],
        "status": "ready",
    }
    assert (await handler.result("a", receipt))["error"]["code"] == "STALE_CONTROL"
    reply = await handler.result("a", {**receipt, "control_revision": 2})
    assert reply["state"]["phase"] == "reading"
    assert all(call.kwargs == {"to": "a"} for call in handler.sio.emit.await_args_list)
    assert all(call.args[0].startswith("earth:") for call in handler.sio.emit.await_args_list)
    await handler.disconnect("a")


async def test_pause_cancels_pending_search_no_late_navigation(handler) -> None:
    started = asyncio.Event()

    async def search(query):
        started.set()
        await asyncio.Event().wait()

    handler.search.search = search
    await control(handler, "open")
    searching = asyncio.create_task(control(handler, "text", text="杭州"))
    await started.wait()
    paused = await control(handler, "pause", revision=1)
    assert paused["ok"] and paused["state"]["phase"] == "paused"
    assert (await searching)["error"]["code"] == "CANCELLED"
    saved = await handler.graph.aget_state(handler.sessions["a"].config)
    assert saved.tasks[0].interrupts
    assert all(call.args[1].get("kind") != "navigate" for call in handler.sio.emit.await_args_list)
    await handler.disconnect("a")
    assert not handler.sessions


async def test_search_failure_still_publishes_current_revision(handler) -> None:
    await control(handler, "open")
    handler.search.search.side_effect = RuntimeError("must not expose private query")
    reply = await control(handler, "text", text="private address")
    assert not reply["ok"] and reply["state"]["control_revision"] == 1
    assert reply["state"]["phase"] == "paused"
    assert "private address" not in str(reply["error"])
    assert (await control(handler, "pause", revision=1))["ok"]
    await handler.disconnect("a")


async def test_disable_prevents_context_and_network(handler, monkeypatch) -> None:
    monkeypatch.setenv("ANIMETTA_EARTH_ENABLED", "false")
    assert (await control(handler, "open"))["error"]["code"] == "EARTH_DISABLED"
    handler.base.get_or_create_context.assert_not_awaited()
    handler.search.search.assert_not_awaited()


async def test_repeated_open_does_not_replay_command_and_reconnect_pauses(handler) -> None:
    await control(handler, "open")
    await control(handler, "text", text="杭州")
    await control(handler, "select", revision=1, candidate_id="r:1")
    handler.sio.emit.reset_mock()
    assert (await control(handler, "open"))["ok"]
    handler.sio.emit.assert_not_awaited()
    await handler.disconnect("a")
    reply = await control(handler, "open", sid="reconnected")
    assert reply["state"]["phase"] == "paused" and reply["state"]["transcript"] == []
    assert all(call.args[0] != "earth:command" for call in handler.sio.emit.await_args_list)
    await handler.disconnect("reconnected")


async def test_stale_pause_returns_current_state_without_interrupting_new_intent(handler) -> None:
    await control(handler, "open")
    await control(handler, "text", text="杭州")
    reply = await control(handler, "pause", revision=0)
    assert reply["error"]["code"] == "STALE_CONTROL"
    assert (
        reply["state"]["phase"] == "waiting_selection" and reply["state"]["control_revision"] == 1
    )
    await handler.disconnect("a")


async def test_first_transition_failure_has_complete_projection(handler, monkeypatch) -> None:
    monkeypatch.setattr(
        "animetta.services.earth.exploration.ExplorationService.apply",
        AsyncMock(side_effect=RuntimeError("initial failure")),
    )
    reply = await control(handler, "open")
    assert not reply["ok"]
    assert reply["state"]["conversation_id"] == "private"
    assert reply["state"]["candidates"] == []
    assert reply["state"]["transcript"] == []
    assert reply["state"]["capabilities"] == {
        "search": True,
        "voice": False,
        "asr": False,
        "vision": False,
        "auto_search": False,
    }
    await handler.disconnect("a")
