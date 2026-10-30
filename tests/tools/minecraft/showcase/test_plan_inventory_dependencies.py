from __future__ import annotations

import json

import pytest

from animetta.acceptance.minecraft_planning import validate_mission_plan
from animetta.tools.minecraft.core.tools import MinecraftExecuteRequest
from animetta.tools.minecraft.mission.models import MissionSpec
from animetta.tools.minecraft.survival.mainline import build_nether_portal_mission
from scripts.minecraft_real_model_contract import (
    _collect_independent_calls,
    _validate_planning_response,
)


def reference() -> MissionSpec:
    mission = build_nether_portal_mission(mission_id="model-plan", home=(0, 64, 0))
    return mission.model_copy(
        update={"execution": mission.execution.model_copy(update={"stop_on_action_failure": True})}
    )


def missing_iron(mission: MissionSpec) -> MissionSpec:
    # Shape of the retained real-model failure: water precedes iron acquisition.
    data = mission.model_dump(mode="json")
    for obj in data["objectives"]:
        if obj["objective_id"] == "water-return":
            obj["dependencies"] = []
    return MissionSpec.model_validate(data)


def test_existing_full_plan_satisfies_known_inventory_dependencies() -> None:
    mission = reference()
    assert validate_mission_plan(mission, reference=mission, initial_inventory={}) == ()


def test_empty_inventory_water_before_iron_returns_actionable_dependency_error() -> None:
    mission = reference()
    issues = validate_mission_plan(missing_iron(mission), reference=mission, initial_inventory={})
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == "MISSING_WORKFLOW_INPUTS"
    assert issue.objective_id == "water-bucket"
    assert issue.candidate_dependencies == ("iron",)
    assert any(
        any(i.item == "iron_ingot" and i.quantity == 3 for i in c.inventory_all)
        for c in issue.required_any_of
    )


@pytest.mark.parametrize(
    "inventory", [{"bucket": 1}, {"minecraft:iron_ingot": 3}, {"water_bucket": 1}]
)
def test_existing_inventory_does_not_force_an_unnecessary_iron_dependency(inventory) -> None:
    mission = reference()
    assert (
        validate_mission_plan(missing_iron(mission), reference=mission, initial_inventory=inventory)
        == ()
    )


def test_inventory_aliases_are_not_added_together() -> None:
    mission = reference()
    issues = validate_mission_plan(
        missing_iron(mission),
        reference=mission,
        initial_inventory={"iron_ingot": 2, "minecraft:iron_ingot": 2},
    )
    assert len(issues) == 1 and issues[0].code == "MISSING_WORKFLOW_INPUTS"


def test_namespaced_predicates_and_reordered_nodes_are_semantically_equivalent() -> None:
    mission = reference()
    data = mission.model_dump(mode="json")
    data["objectives"].reverse()
    for obj in data["objectives"]:
        for predicate in obj["goal"]["success_predicates"]:
            if predicate["kind"] == "inventory_at_least":
                predicate["item"] = "minecraft:" + predicate["item"]
    plan = MissionSpec.model_validate(data)
    assert validate_mission_plan(plan, reference=mission, initial_inventory={}) == ()


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("budget", "PLAN_AUTHORITY_MISMATCH"),
        ("scope", "PLAN_SCOPE_MISMATCH"),
        ("item", "PLAN_GOAL_MISMATCH"),
    ],
)
def test_planner_cannot_relax_authority_or_change_the_goal(mutation, code) -> None:
    mission = reference()
    data = mission.model_dump(mode="json")
    if mutation == "budget":
        data["budget"]["max_actions"] += 1
    elif mutation == "scope":
        data["objectives"].pop()
    else:
        data["objectives"][0]["goal"]["success_predicates"][0]["item"] = "other:iron_ingot"
    issues = validate_mission_plan(
        MissionSpec.model_validate(data), reference=mission, initial_inventory={}
    )
    assert issues and issues[0].code == code


def test_missing_dependency_is_reported_without_mutating_the_plan() -> None:
    mission = reference()
    plan = missing_iron(mission)
    before = plan.model_dump(mode="json")
    validate_mission_plan(plan, reference=mission, initial_inventory={})
    assert plan.model_dump(mode="json") == before


async def test_structured_input_error_reaches_the_existing_model_repair_once() -> None:
    mission = reference()
    authority = MinecraftExecuteRequest.model_validate(
        {
            "kind": "mission",
            "request_id": "model-plan:mainline:v1",
            "mission": mission.model_dump(mode="json"),
        }
    )

    def response(plan):
        return {
            "tool_calls": [
                {
                    "name": "mc_operate_bot",
                    "id": "plan-call",
                    "args": {
                        "operation": "execute",
                        "execute": {
                            "kind": "mission",
                            "request_id": authority.request_id,
                            "mission": plan.model_dump(mode="json"),
                        },
                    },
                }
            ]
        }

    broken = response(missing_iron(mission))
    original = json.dumps(broken, sort_keys=True)
    model_calls = 0

    async def invoke(_user_text, history):
        nonlocal model_calls
        model_calls += 1
        if model_calls == 1:
            return broken
        result = json.loads(history[-1].content)
        assert result["gameplay_submitted"] is False
        assert result["repair_remaining"] is True
        problem = json.loads(result["error"])
        assert problem["code"] == "MC_PLAN_REJECTED"
        assert problem["issues"][0]["candidate_dependencies"] == ["iron"]
        return response(mission)

    calls = await _collect_independent_calls(
        invoke=invoke,
        validate=lambda candidate: _validate_planning_response(
            candidate, reference=authority, initial_inventory={}
        ),
        independent_calls=1,
        user_text="plan portal",
        max_attempts=2,
    )
    assert model_calls == 2
    assert len(calls[0]["attempts"]) == 2
    assert calls[0]["final_validation"]["valid"] is True
    assert json.dumps(broken, sort_keys=True) == original
