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


def unprovisioned_descent(mission: MissionSpec) -> MissionSpec:
    # R95 kept the water goal independent of the deep mining goal.
    data = mission.model_dump(mode="json")
    dependencies = {
        "diamond-pickaxe": ["iron-pickaxe"],
        "water-return": ["iron-pickaxe"],
        "water-bucket": ["water-return"],
        "ignition": ["iron"],
        "obsidian": ["diamond-pickaxe", "water-bucket"],
    }
    for objective in data["objectives"]:
        if objective["objective_id"] in dependencies:
            objective["dependencies"] = dependencies[objective["objective_id"]]
    return MissionSpec.model_validate(data)


def stale_iron_shore(mission: MissionSpec) -> MissionSpec:
    # R96: the visited shore precedes mining; water only waits for the iron kit.
    data = mission.model_dump(mode="json")
    dependencies = {
        "water-return": [],
        "iron": ["water-return"],
        "water-bucket": ["iron"],
        "diamond-pickaxe": ["iron-pickaxe", "water-bucket"],
    }
    for objective in data["objectives"]:
        if objective["objective_id"] in dependencies:
            objective["dependencies"] = dependencies[objective["objective_id"]]
    return MissionSpec.model_validate(data)


@pytest.mark.parametrize(
    "inventory,valid",
    [
        ({}, False),
        ({"water_bucket": 1}, True),
        ({"minecraft:iron_ingot": 7}, True),
        ({"iron_ingot": 4, "minecraft:iron_ingot": 4}, False),
    ],
)
def test_iron_before_water_requires_a_fresh_return_unless_already_provisioned(
    inventory, valid
) -> None:
    mission = reference()
    plan = stale_iron_shore(mission)
    before = plan.canonical_hash
    issues = validate_mission_plan(plan, reference=mission, initial_inventory=inventory)
    assert [issue.code for issue in issues] == ([] if valid else ["MISSING_ACCESS_PROVISION"])
    if not valid:
        assert issues[0].objective_id == "water-bucket"
        assert issues[0].candidate_dependencies == ("water-return",)
        assert issues[0].required_any_of == ()
    assert plan.canonical_hash == before


def test_iron_can_return_to_the_same_shore_using_another_authorized_travel_goal() -> None:
    mission = reference()
    data = stale_iron_shore(mission).model_dump(mode="json")
    for objective in data["objectives"]:
        if objective["objective_id"] == "return-home":
            objective["dependencies"] = ["iron"]
        elif objective["objective_id"] == "water-bucket":
            objective["dependencies"] = ["return-home"]
        elif objective["objective_id"] == "portal":
            objective["dependencies"] = ["return-home", "obsidian", "ignition"]
    plan = MissionSpec.model_validate(data)
    assert validate_mission_plan(plan, reference=mission, initial_inventory={}) == ()


def test_deep_mining_cannot_spend_surface_access_before_an_independent_water_goal() -> None:
    mission = reference()
    plan = unprovisioned_descent(mission)
    before = plan.model_dump(mode="json")
    issues = validate_mission_plan(plan, reference=mission, initial_inventory={})
    assert len(issues) == 1
    assert issues[0].code == "MISSING_ACCESS_PROVISION"
    assert issues[0].objective_id == "diamond-pickaxe"
    assert issues[0].candidate_dependencies == ("water-bucket",)
    assert issues[0].required_any_of == (), "access is not a diamond recipe ingredient"
    assert plan.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "inventory", [{"water_bucket": 1}, {"minecraft:diamond": 3}, {"diamond_pickaxe": 1}]
)
def test_existing_provision_or_local_diamond_craft_preserves_order_freedom(inventory) -> None:
    mission = reference()
    assert (
        validate_mission_plan(
            unprovisioned_descent(mission), reference=mission, initial_inventory=inventory
        )
        == ()
    )


def test_explicit_shore_return_after_descent_can_supply_water_without_forcing_water_first() -> None:
    mission = reference()
    data = unprovisioned_descent(mission).model_dump(mode="json")
    for objective in data["objectives"]:
        if objective["objective_id"] == "water-return":
            objective["dependencies"] = ["diamond-pickaxe"]
        elif objective["objective_id"] == "water-bucket":
            objective["dependencies"] = ["water-return"]
    plan = MissionSpec.model_validate(data)
    assert validate_mission_plan(plan, reference=mission, initial_inventory={}) == ()


def test_a_shore_fact_before_descent_and_split_diamond_aliases_do_not_prove_access() -> None:
    mission = reference()
    data = unprovisioned_descent(mission).model_dump(mode="json")
    for objective in data["objectives"]:
        if objective["objective_id"] == "water-bucket":
            objective["dependencies"] = ["water-return"]
    issues = validate_mission_plan(
        MissionSpec.model_validate(data),
        reference=mission,
        initial_inventory={"diamond": 2, "minecraft:diamond": 2},
    )
    assert [issue.code for issue in issues] == ["MISSING_ACCESS_PROVISION"]


@pytest.mark.parametrize(
    "shore_x,tolerance,valid", [(0, 1.5, True), (10, 1.5, False), (0, 3, False)]
)
def test_return_access_uses_the_authorized_location_region_instead_of_its_label(
    shore_x, tolerance, valid
) -> None:
    data = reference().model_dump(mode="json")
    for objective in data["objectives"]:
        if objective["objective_id"] == "return-home":
            predicate = objective["goal"]["success_predicates"][0]
            predicate.update(x=shore_x, tolerance=tolerance)
    mission = MissionSpec.model_validate(data)
    data = unprovisioned_descent(mission).model_dump(mode="json")
    for objective in data["objectives"]:
        if objective["objective_id"] == "return-home":
            objective["dependencies"] = ["diamond-pickaxe"]
        elif objective["objective_id"] == "water-bucket":
            objective["dependencies"] = ["return-home"]
    issues = validate_mission_plan(
        MissionSpec.model_validate(data), reference=mission, initial_inventory={"iron_ingot": 7}
    )
    assert [issue.code for issue in issues] == ([] if valid else ["MISSING_ACCESS_PROVISION"])


def test_a_standalone_diamond_goal_does_not_invent_a_water_task() -> None:
    data = reference().model_dump(mode="json")
    diamond = next(
        objective
        for objective in data["objectives"]
        if objective["objective_id"] == "diamond-pickaxe"
    )
    diamond["dependencies"] = []
    data["objectives"] = [diamond]
    mission = MissionSpec.model_validate(data)
    assert validate_mission_plan(mission, reference=mission, initial_inventory={}) == ()


def test_existing_full_plan_satisfies_known_inventory_dependencies() -> None:
    mission = reference()
    assert validate_mission_plan(mission, reference=mission, initial_inventory={}) == ()


@pytest.mark.parametrize("inventory", [{}, {"bucket": 1}, {"iron_ingot": 3}])
def test_obsidian_preparation_needs_water_provisioned_before_its_goal(inventory) -> None:
    mission = reference()
    data = mission.model_dump(mode="json")
    for objective in data["objectives"]:
        if objective["objective_id"] == "diamond-pickaxe":
            objective["dependencies"] = ["iron-pickaxe"]
        if objective["objective_id"] == "obsidian":
            objective["dependencies"] = ["diamond-pickaxe"]
    plan = MissionSpec.model_validate(data)
    original = plan.canonical_hash
    # Local diamond stock isolates the obsidian-input check from deep-access planning.
    issues = validate_mission_plan(
        plan, reference=mission, initial_inventory={**inventory, "diamond": 3}
    )
    assert len(issues) == 1 and issues[0].objective_id == "obsidian"
    assert issues[0].code == "MISSING_WORKFLOW_INPUTS"
    assert issues[0].candidate_dependencies == ("water-bucket",)
    assert all(
        any(item.item == "water_bucket" for item in clause.inventory_all)
        for clause in issues[0].required_any_of
        if not any(item.item == "obsidian" for item in clause.inventory_all)
    )
    assert plan.canonical_hash == original
    for supplied in [{"water_bucket": 1}, {"minecraft:obsidian": 10}]:
        assert (
            validate_mission_plan(
                plan, reference=mission, initial_inventory={**supplied, "diamond": 3}
            )
            == ()
        )


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


@pytest.mark.parametrize("failure_kind", ["inventory", "access", "shore"])
async def test_structured_input_error_reaches_the_existing_model_repair_once(failure_kind) -> None:
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

    broken = response(
        {"inventory": missing_iron, "access": unprovisioned_descent, "shore": stale_iron_shore}[
            failure_kind
        ](mission)
    )
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
        assert (
            problem["issues"][0]["candidate_dependencies"]
            == {
                "inventory": ["iron"],
                "access": ["water-bucket"],
                "shore": ["water-return"],
            }[failure_kind]
        )
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
