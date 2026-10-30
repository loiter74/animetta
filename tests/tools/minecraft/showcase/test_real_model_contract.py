from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from animetta.acceptance.minecraft_showcase import (
    _added_advancement_ids,
    _mission_advancement_events,
    _normalize_model_execute_args,
)
from animetta.tools.minecraft.core.tools import MinecraftOperateToolInput
from animetta.tools.minecraft.mission.schema import build_golden_fixture
from scripts.minecraft_real_model_contract import (
    _collect_independent_calls,
    _starter_shelter_budget_admissible,
    _starter_shelter_static_cost,
)


async def test_model_collector_keeps_custom_task_and_provided_connection_context() -> None:
    task = "从空背包规划到点亮地狱门"
    status = {"state": "ready", "profile": "independent-portal", "generation_id": 7}
    prompts = []

    async def invoke(user_text, history):
        prompts.append(user_text)
        if len(prompts) == 1:
            assert user_text == task
            return {
                "tool_calls": [
                    {"name": "mc_connection", "args": {"operation": "status"}, "id": "status-1"}
                ]
            }
        assert json.loads(history[-1].content) == status
        assert history[0].content == task
        return {"content": "portal-plan", "tool_calls": []}

    calls = await _collect_independent_calls(
        invoke=invoke,
        validate=lambda response: ({"valid": response.get("content") == "portal-plan"}, None),
        independent_calls=1,
        user_text=task,
        connection_status=status,
        max_attempts=1,
    )
    assert calls[0]["final_validation"]["valid"]
    assert len(prompts) == 2
    assert status == {"state": "ready", "profile": "independent-portal", "generation_id": 7}


async def test_single_attempt_model_collector_records_failure_without_another_call() -> None:
    prompts = []

    async def invoke(user_text, _history):
        prompts.append(user_text)
        return {"tool_calls": [], "usage": {"total_tokens": 11}}

    calls = await _collect_independent_calls(
        invoke=invoke,
        validate=lambda _response: ({"valid": False}, "invalid plan"),
        independent_calls=1,
        user_text="portal task",
        max_attempts=1,
    )
    assert prompts == ["portal task"]
    assert calls[0]["final_validation"]["valid"] is False
    assert calls[0]["attempts"][0]["usage"] == {"total_tokens": 11}


@pytest.mark.parametrize("attempts", [0, 3])
async def test_model_collector_cannot_raise_existing_repair_attempt_limit(attempts) -> None:
    async def invoke(_user_text, _history):
        raise AssertionError("invalid limits must not call a model")

    with pytest.raises(ValueError, match="max_attempts"):
        await _collect_independent_calls(invoke=invoke, max_attempts=attempts)


async def test_model_collector_does_not_turn_provided_disconnected_status_into_ready() -> None:
    count = 0

    async def invoke(user_text, history):
        nonlocal count
        count += 1
        if count == 1:
            return {
                "tool_calls": [
                    {"name": "mc_connection", "args": {"operation": "status"}, "id": "status-1"}
                ]
            }
        assert json.loads(history[-1].content) == {"state": "disconnected"}
        assert "已确认 ready" not in user_text
        return {"tool_calls": []}

    calls = await _collect_independent_calls(
        invoke=invoke,
        validate=lambda _response: ({"valid": False}, "not connected"),
        independent_calls=1,
        user_text="portal",
        connection_status={"state": "disconnected"},
        max_attempts=1,
    )
    assert calls[0]["final_validation"]["valid"] is False
    assert calls[0]["attempts"][0]["model_calls"] == count == 2


@pytest.mark.parametrize("validation_error", [False, True])
async def test_real_model_runner_passes_task_contract_and_closes_its_provider(
    monkeypatch,
    tmp_path,
    validation_error,
) -> None:
    from scripts import minecraft_real_model_contract as contract

    class Provider:
        closed = False

        async def chat_with_tools(self, user_text, **_kwargs):
            assert user_text == "portal task"
            return {"content": "portal plan", "tool_calls": []}

        def consume_usage(self):
            return None

        async def close(self):
            self.closed = True

    provider = Provider()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-provider-key")
    monkeypatch.setattr(contract.OpenAILLM, "from_config", lambda _config: provider)

    def validate(response):
        assert response["content"] == "portal plan"
        if validation_error:
            raise ValueError("invalid task contract")
        return {"valid": True}, None

    async def run():
        return await contract.run(
            tmp_path,
            independent_calls=1,
            user_text="portal task",
            validate=validate,
            max_attempts=1,
            connection_status={"state": "ready"},
        )

    if validation_error:
        with pytest.raises(ValueError, match="invalid task contract"):
            await run()
    else:
        result = json.loads((await run()).read_text(encoding="utf-8"))
        assert result["exact_user_text"] == "portal task"
        assert result["max_attempts_per_conversation"] == 1
        assert result["connection_context_source"] == "provided"
        assert result["model_calls"] == 1
        assert result["calls"][0]["attempts"][0]["model_usages"] == [None]
        assert result["gameplay_executed"] is False
    assert provider.closed


async def test_real_model_gate_uses_three_fresh_independent_conversations() -> None:
    history_lengths: list[int] = []

    async def invoke(user_text, history):
        assert user_text
        history_lengths.append(len(history))
        return {"content": "ok", "tool_calls": []}

    def validate(_response):
        return {"valid": True, "semantic_assertions": {"all": True}}, None

    calls = await _collect_independent_calls(
        invoke=invoke,
        validate=validate,
        independent_calls=3,
    )

    assert len(calls) == 3
    assert history_lengths == [0, 0, 0]
    assert all(call["final_validation"]["valid"] for call in calls)


async def test_real_model_gate_strips_internal_tool_call_diagnostics_from_history() -> None:
    invocations = 0

    async def invoke(_user_text, history):
        nonlocal invocations
        invocations += 1
        if invocations == 2:
            history_call = history[1].tool_calls[0]
            assert history_call == {
                "name": "mc_operate_bot",
                "args": {"operation": "execute"},
                "id": "call-1",
                "type": "tool_call",
            }
            return {"content": "fixed", "tool_calls": []}
        return {
            "content": "repair me",
            "tool_calls": [
                {
                    "name": "mc_operate_bot",
                    "args": {"operation": "execute"},
                    "id": "call-1",
                    "type": "tool_call",
                    "arguments_repaired": True,
                }
            ],
        }

    def validate(response):
        valid = response.get("content") == "fixed"
        return {"valid": valid}, None if valid else "repair"

    calls = await _collect_independent_calls(
        invoke=invoke,
        validate=validate,
        independent_calls=1,
    )

    assert calls[0]["final_validation"]["valid"] is True


async def test_real_model_gate_answers_connection_preflight_before_execute() -> None:
    invocations = 0

    async def invoke(_user_text, history):
        nonlocal invocations
        invocations += 1
        if invocations == 1:
            return {
                "content": "checking",
                "tool_calls": [
                    {
                        "name": "mc_connection",
                        "args": {"operation": "status", "request_id": "status-1"},
                        "id": "status-call-1",
                    }
                ],
            }
        assert json.loads(history[-1].content)["state"] == "ready"
        return {
            "content": "submitting",
            "tool_calls": [
                {
                    "name": "mc_operate_bot",
                    "args": {"operation": "execute"},
                    "id": "execute-call-1",
                }
            ],
        }

    def validate(response):
        valid = response["tool_calls"][0]["name"] == "mc_operate_bot"
        return {"valid": valid}, None if valid else "wrong tool"

    calls = await _collect_independent_calls(
        invoke=invoke,
        validate=validate,
        independent_calls=1,
    )

    assert calls[0]["final_validation"]["valid"] is True
    assert calls[0]["attempts"][0]["preflight_tool_calls"][0]["name"] == "mc_connection"


def test_real_model_gate_rejects_shelter_budget_below_compiled_cost() -> None:
    static_cost = _starter_shelter_static_cost()
    assert static_cost.max_actions == 83
    assert static_cost.max_blocks_changed == 85

    insufficient = SimpleNamespace(
        objectives=(
            SimpleNamespace(
                goal=SimpleNamespace(
                    success_predicates=(
                        SimpleNamespace(
                            blueprint_id="starter-shelter-v1",
                        ),
                    ),
                ),
                budget=SimpleNamespace(max_actions=80, max_blocks_changed=80),
            ),
        ),
    )
    admissible = SimpleNamespace(
        objectives=(
            SimpleNamespace(
                goal=SimpleNamespace(
                    success_predicates=(
                        SimpleNamespace(
                            blueprint_id="starter-shelter-v1",
                        ),
                    ),
                ),
                budget=SimpleNamespace(max_actions=84, max_blocks_changed=85),
            ),
        ),
    )

    assert _starter_shelter_budget_admissible(insufficient) is False
    assert _starter_shelter_budget_admissible(admissible) is True


def test_real_model_gate_recovers_unambiguous_missing_mission_discriminator() -> None:
    args = {
        "operation": "execute",
        "execute": {
            "request_id": "survival-showcase-v1",
            "mission": build_golden_fixture()["mission_spec"],
        },
    }

    normalized = _normalize_model_execute_args(args)
    validated = MinecraftOperateToolInput.model_validate(normalized)

    assert normalized is not args
    assert normalized["execute"]["kind"] == "mission"
    assert validated.execute is not None
    assert validated.execute.request.kind == "mission"


def test_real_model_gate_does_not_rewrite_ambiguous_or_atomic_input() -> None:
    mission = build_golden_fixture()["mission_spec"]

    ambiguous = {
        "operation": "execute",
        "execute": {"request_id": "ambiguous-v1", "mission": mission, "action": {}},
    }
    atomic = {
        "operation": "execute",
        "execute": {"request_id": "atomic-v1", "action": {"kind": "observe"}},
    }

    assert _normalize_model_execute_args(ambiguous) == ambiguous
    assert _normalize_model_execute_args(atomic) == atomic


def test_final_evidence_projects_added_vanilla_advancements() -> None:
    events = (
        SimpleNamespace(action="add", advancement_id="minecraft:adventure/root"),
        SimpleNamespace(action="remove", advancement_id="minecraft:story/root"),
        SimpleNamespace(action="add", advancement_id="minecraft:adventure/kill_a_mob"),
    )

    assert _added_advancement_ids(events) == [
        "minecraft:adventure/root",
        "minecraft:adventure/kill_a_mob",
    ]


async def test_final_evidence_uses_successful_mission_command_when_last_command_failed() -> None:
    first = SimpleNamespace(
        content_hash="event-1",
        observed_at_ms=1,
        action="add",
        advancement_id="minecraft:adventure/adventuring_time",
    )
    second = SimpleNamespace(
        content_hash="event-2",
        observed_at_ms=2,
        action="add",
        advancement_id="minecraft:adventure/kill_all_mobs",
    )

    class Collector:
        async def current_advancement_events(self, command_id):
            if command_id == "failed-build":
                return ()
            return (first, second)

    events = await _mission_advancement_events(
        Collector(),
        ("successful-combat", "failed-build"),
    )

    assert events == (first, second)
