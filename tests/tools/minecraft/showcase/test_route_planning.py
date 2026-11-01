"""Model route drafts cannot replace authority, blueprint geometry, or quotas."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from animetta.acceptance.minecraft_planning import inventory_input_options
from animetta.acceptance.minecraft_route_generation import generate_route_plan
from animetta.acceptance.minecraft_route_planning import (
    RouteDraft,
    RoutePlanningError,
    compile_route_draft,
    route_prompt_context,
)
from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.survival.mainline import build_nether_portal_mission
from animetta.tools.minecraft.survival.workflows import (
    InventoryThreshold,
    WorkflowCheckpoint,
    WorkflowCheckpointClause,
)
from animetta.tools.minecraft.voyager.goal_models import InventoryAtLeast
from animetta.tools.minecraft.voyager.strategies.builtin import BuiltinMissionStrategy

MESSAGES = json.loads(
    (Path(__file__).resolve().parents[4] / "contracts/gamebot/v2/fixtures/golden.json").read_text(
        "utf-8"
    )
)["messages"]
ROUTE = [
    "iron",
    "iron-pickaxe",
    "water-return",
    "water-bucket",
    "ignition",
    "diamond-pickaxe",
    "obsidian",
    "return-home",
    "portal",
]


def manifest():
    return RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])


def compile_draft(payload, inventory=None):
    return compile_route_draft(
        RouteDraft.model_validate(payload),
        mission_id="route-test",
        home=(0, 64, 0),
        origin=(2, 64, 0),
        manifest=manifest(),
        initial_inventory=inventory or {},
    )


def skill():
    return {
        "task": "diamond-pickaxe",
        "name": "bounded_test_skill",
        "steps": [
            {
                "kind": "action",
                "step_id": "gather",
                "capability": "collect",
                "parameters": {"count": {"kind": "goal_input", "name": "quantity"}},
                "maximum_cost": manifest()
                .capability("collect")
                .maximum_cost.model_dump(mode="json", exclude={"protected_items"}),
            }
        ],
    }


def test_short_route_retains_original_budget_and_builtin_blueprint():
    mission = compile_draft({"route": ROUTE})
    old = build_nether_portal_mission(mission_id="route-test", home=(0, 64, 0))
    assert mission.budget == old.budget
    assert mission.autonomy.max_new_skills == 1
    assert [o.objective_id for o in mission.objectives] == ROUTE
    assert (
        mission.objectives[-1].goal.success_predicates == old.objectives[-1].goal.success_predicates
    )
    assert "skill_candidate" not in mission.objectives[-1].goal.constraints
    builtin = BuiltinMissionStrategy(
        manifest=manifest(), blueprint_origins={"nether-portal-v1": (2, 64, 0)}
    )
    state = builtin.prepare(mission.objectives[-1].goal)
    assert state["kind"] == "blueprint"
    assert (
        state["blueprint"].canonical_hash
        == mission.objectives[-1].goal.success_predicates[0].blueprint_hash
    )


def test_route_does_not_require_old_nine_if_verified_inputs_already_exist():
    mission = compile_draft(
        {"route": ["portal"]}, {"obsidian": 10, "flint_and_steel": 1, "cobbled_deepslate": 4}
    )
    assert len(mission.objectives) == 1 and mission.budget.max_actions == 117


@pytest.mark.parametrize("extra", ["mission_id", "coordinates", "blueprint", "budget"])
def test_model_cannot_rewrite_host_fields(extra):
    with pytest.raises(ValidationError):
        RouteDraft.model_validate({"route": ROUTE, extra: {}})


def test_small_skill_uses_host_types_and_goal_postconditions():
    mission = compile_draft({"route": ROUTE, "skill": skill()})
    learned = next(o for o in mission.objectives if o.objective_id == "diamond-pickaxe")
    program = learned.goal.constraints["skill_candidate"]["program"]
    types = {p["name"]: p["value_type"] for p in program["parameters"]}
    assert types["home_x"] == types["quantity"] == "integer"
    assert program["postconditions"][0]["left"]["path"] == "inventory.diamond_pickaxe"
    assert all("frame_" not in p["name"] for p in program["parameters"])
    for forbidden in ("parameters", "postconditions"):
        bad = skill() | {forbidden: []}
        with pytest.raises(ValidationError):
            compile_draft({"route": ROUTE, "skill": bad})


def test_skill_cannot_take_over_portal_or_escape_child_budget():
    with pytest.raises(RoutePlanningError, match="SKILL_SCOPE_FORBIDDEN"):
        compile_draft({"route": ROUTE, "skill": skill() | {"task": "portal"}})
    bad = skill()
    bad["steps"][0]["maximum_cost"]["max_actions"] = 999
    with pytest.raises(RoutePlanningError, match="SKILL_COMPILE_FAILED"):
        compile_draft({"route": ROUTE, "skill": bad})
    with pytest.raises(ValidationError):
        compile_draft({"route": ROUTE, "skill": [skill(), skill()]})


def test_missing_portal_materials_are_reported_together():
    with pytest.raises(RoutePlanningError) as failure:
        compile_draft({"route": ["portal"]})
    assert {i["item"] for i in failure.value.issues if i["code"] == "MISSING_PORTAL_INPUT"} == {
        "obsidian",
        "flint_and_steel",
    }


async def test_generation_repairs_within_two_proposals_and_preserves_failed_evidence():
    calls = []
    recorded = []

    async def invoke(messages):
        calls.append(messages)
        return {
            "content": '{"route":["portal"]}' if len(calls) == 1 else json.dumps({"route": ROUTE}),
            "usage": {"output_tokens": 10},
        }

    result = await generate_route_plan(
        invoke=invoke,
        messages=[{"role": "user", "content": "JSON route"}],
        mission_id="route-test",
        home=(0, 64, 0),
        origin=(2, 64, 0),
        manifest=manifest(),
        initial_inventory={},
        on_attempt=recorded.append,
    )
    assert result.mission is not None and len(result.attempts) == len(calls) == 2
    assert len(result.attempts[0].issues) == 2
    assert recorded == list(result.attempts)
    assert json.loads(calls[1][-1]["content"])["remaining_proposals"] == 1


async def test_malformed_generation_stops_at_original_total_limit():
    calls = []

    async def invoke(messages):
        calls.append(messages)
        return {"content": "{", "usage": None}

    result = await generate_route_plan(
        invoke=invoke,
        messages=[],
        mission_id="route-test",
        home=(0, 64, 0),
        origin=(2, 64, 0),
        manifest=manifest(),
        initial_inventory={},
    )
    assert result.mission is None and len(result.attempts) == len(calls) == 2


def test_route_prompt_keeps_voxel_dump_and_frame_bindings_outside_model_authority():
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "environment": {"dimension": "minecraft:overworld", "voxel_payload": "x" * 50000},
        }
    )
    context = route_prompt_context(
        mission_id="route-test", home=(0, 64, 0), observation=observation, manifest=manifest()
    )
    encoded = json.dumps(context)
    assert "voxel_payload" not in encoded and "frame_x0" not in encoded
    assert len(context["observation"]["nearby_block_samples"]) <= 16
    assert {p["name"] for p in context["host_skill_parameters"]} == {
        "target",
        "quantity",
        "home_x",
        "home_y",
        "home_z",
    }


async def test_native_allocation_guard_failure_is_not_returned_as_success():
    bad_skill = skill()
    bad_skill["steps"][0]["maximum_cost"]["max_actions"] = 17
    calls = []

    async def invoke(messages):
        calls.append(messages)
        draft = {"route": ROUTE, "skill": bad_skill} if len(calls) == 1 else {"route": ROUTE}
        return {"content": json.dumps(draft), "usage": None}

    def guard(mission):
        for objective in mission.objectives:
            candidate = objective.goal.constraints.get("skill_candidate")
            if candidate and candidate["program"]["steps"][0]["maximum_cost"]["max_actions"] > 16:
                raise ValueError("native action allocation exceeds unchanged ceiling")

    result = await generate_route_plan(
        invoke=invoke,
        messages=[],
        mission_id="route-test",
        home=(0, 64, 0),
        origin=(2, 64, 0),
        manifest=manifest(),
        initial_inventory={},
        validate_mission=guard,
    )
    assert len(result.attempts) == len(calls) == 2
    assert result.attempts[0].issues and result.mission is not None


def test_r102_omitted_supplier_is_reported_from_the_full_catalogue():
    route = [task for task in ROUTE if task != "diamond-pickaxe"]
    with pytest.raises(RoutePlanningError) as failure:
        compile_draft({"route": route})
    assert len(failure.value.issues) == 1
    issue = failure.value.issues[0]
    assert issue["code"] == "MISSING_WORKFLOW_INPUTS"
    assert issue["objective_id"] == "obsidian"
    assert issue["candidate_dependencies"] == []
    diamond, water = issue["input_options"][1]["inventory_all"]
    assert diamond == {
        "item": "minecraft:diamond_pickaxe",
        "quantity": 1,
        "available_quantity": 0,
        "missing_quantity": 1,
        "supplier_tasks": ["diamond-pickaxe"],
    }
    assert water["missing_quantity"] == 0 and water["supplier_tasks"] == []
    assert issue["input_options"][0]["inventory_all"][0]["supplier_tasks"] == []
    assert issue["input_options"][2]["inventory_all"][0]["supplier_tasks"] == []
    assert "diamond-pickaxe" not in route, "validation must not silently rewrite the draft"
    repaired = compile_draft({"route": ROUTE})
    assert (
        repaired.budget
        == build_nether_portal_mission(mission_id="route-test", home=(0, 64, 0)).budget
    )


def test_prompt_and_feedback_share_inventory_options():
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"inventory": {}}
    )
    context = route_prompt_context(
        mission_id="route-test", home=(0, 64, 0), observation=observation, manifest=manifest()
    )
    catalogue = {task["task"]: task for task in context["catalogue"]}
    with pytest.raises(RoutePlanningError) as failure:
        compile_draft({"route": ["obsidian", "portal"]})
    obsidian = next(i for i in failure.value.issues if i.get("objective_id") == "obsidian")
    assert obsidian["input_options"] == catalogue["obsidian"]["default_workflow_inputs"]
    assert catalogue["portal"]["default_workflow_inputs"][0]["inventory_all"][0][
        "supplier_tasks"
    ] == ["obsidian"]


def test_selected_later_supplier_is_a_reordering_choice_not_a_new_dependency_edge():
    route = ROUTE.copy()
    route.remove("diamond-pickaxe")
    route.insert(route.index("obsidian") + 1, "diamond-pickaxe")
    with pytest.raises(RoutePlanningError) as failure:
        compile_draft({"route": route})
    issue = next(i for i in failure.value.issues if i.get("objective_id") == "obsidian")
    assert issue["candidate_dependencies"] == [], "adding this descendant would create a cycle"
    assert issue["input_options"][1]["inventory_all"][0]["supplier_tasks"] == ["diamond-pickaxe"]
    assert "重排" in issue["message"]
    assert compile_draft({"route": ROUTE}).objectives[-1].objective_id == "portal"


def test_inventory_resolver_is_not_tied_to_portal_recipes_or_additive_aliases():
    contract = WorkflowCheckpoint(
        any_of=(
            WorkflowCheckpointClause(
                inventory_all=(
                    InventoryThreshold(item="example", quantity=10),
                    InventoryThreshold(item="minecraft:example", quantity=12),
                )
            ),
        )
    )

    def goal(*quantities):
        template = (
            build_nether_portal_mission(mission_id="route-test", home=(0, 64, 0)).objectives[0].goal
        )
        return template.model_copy(
            update={
                "target": "example",
                "quantity": 12,
                "success_predicates": tuple(
                    InventoryAtLeast(kind="inventory_at_least", item=item, quantity=quantity)
                    for item, quantity in quantities
                ),
            }
        )

    suppliers = {
        "consumer": goal(("example", 12)),
        "too-small": goal(("example", 8), ("minecraft:example", 8)),
        "custom-supplier": goal(("minecraft:example", 12)),
    }
    option = inventory_input_options(
        contract,
        known_inventory={"example": 7, "minecraft:example": 8},
        supplier_goals=suppliers,
        consumer_id="consumer",
    )[0]
    assert not option.satisfied and len(option.inventory_all) == 1
    item = option.inventory_all[0]
    assert (item.item, item.quantity, item.available_quantity, item.missing_quantity) == (
        "minecraft:example",
        12,
        8,
        4,
    )
    assert item.supplier_tasks == ("custom-supplier",)
    satisfied = inventory_input_options(
        contract,
        known_inventory={"minecraft:example": 12},
        supplier_goals=suppliers,
        consumer_id="consumer",
    )[0]
    assert satisfied.satisfied and satisfied.inventory_all[0].supplier_tasks == ()


def test_verified_stock_skips_an_unneeded_supplier_and_generated_skill_skips_default_inputs():
    route = [task for task in ROUTE if task != "diamond-pickaxe"]
    assert compile_draft({"route": route}, {"minecraft:diamond_pickaxe": 1})
    learned = skill() | {"task": "obsidian"}
    # Golden collect's damage cap exceeds obsidian's allowance. Keep that rejection,
    # but do not also enforce the default mining recipe on its replacement program.
    with pytest.raises(RoutePlanningError) as failure:
        compile_draft({"route": route, "skill": learned})
    assert {issue["code"] for issue in failure.value.issues} == {"SKILL_COMPILE_FAILED"}


async def test_r102_feedback_names_the_missing_task_within_the_original_two_proposals():
    calls = []

    async def invoke(messages):
        calls.append(messages)
        route = [task for task in ROUTE if task != "diamond-pickaxe"]
        if len(calls) == 2:
            feedback = json.loads(messages[-1]["content"])
            issue = feedback["issues"][0]
            supplier = issue["input_options"][1]["inventory_all"][0]["supplier_tasks"][0]
            route.insert(route.index("obsidian"), supplier)
        return {"content": json.dumps({"route": route}), "usage": None}

    result = await generate_route_plan(
        invoke=invoke,
        messages=[],
        mission_id="route-test",
        home=(0, 64, 0),
        origin=(2, 64, 0),
        manifest=manifest(),
        initial_inventory={},
    )
    assert result.mission is not None and len(calls) == len(result.attempts) == 2
    assert [obj.objective_id for obj in result.mission.objectives] == ROUTE
    assert result.mission.budget.max_actions == 117
