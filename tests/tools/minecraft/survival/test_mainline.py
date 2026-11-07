"""Survival mainline keeps prerequisite order and verifies activation independently."""

import json
from pathlib import Path

import pytest

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.blueprint import (
    BlueprintBinding,
    BlueprintCompiler,
)
from animetta.tools.minecraft.blueprint.portal import nether_portal_blueprint
from animetta.tools.minecraft.blueprint.verifier import BlueprintVerifier
from animetta.tools.minecraft.core.assembly import _budget_policy
from animetta.tools.minecraft.core.config import MinecraftConfig
from animetta.tools.minecraft.survival.mainline import build_nether_portal_mission
from animetta.tools.minecraft.survival.registry import WorkflowRegistry
from animetta.tools.minecraft.survival.wood import inventory_resource_count
from animetta.tools.minecraft.survival.workflows import (
    WorkflowDefinition,
    nether_preparation_workflows,
)
from animetta.tools.minecraft.voyager.budget import (
    BudgetAccount,
    BudgetUsage,
    RequestedBudget,
    effective_budget,
)
from animetta.tools.minecraft.voyager.goal_verifier import GoalVerifier
from animetta.tools.minecraft.voyager.strategies.builtin import BuiltinMissionStrategy
from animetta.tools.minecraft.voyager.strategies.fallback import FallbackStrategy

MESSAGES = json.loads(
    (Path(__file__).resolve().parents[4] / "contracts/gamebot/v2/fixtures/golden.json").read_text(
        encoding="utf-8"
    )
)["messages"]


def test_partial_wood_stock_advances_when_mixed_recipe_materials_are_observed():
    mission = build_nether_portal_mission(mission_id="partial-wood-substitution")
    workflow = next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    registry = WorkflowRegistry()
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(mission.objectives[0].goal)
    state["budget_remaining"] = mission.budget.model_copy(
        update=mission.objectives[0].budget.model_dump()
    )
    # R80's terminal stock and typed visible species; this does not claim that
    # every observed oak was reachable in the original world.
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "position": {"x": -167, "y": 72, "z": 54},
            "inventory": {"jungle_log": 4},
            "visible_blocks": [
                {"block_id": "minecraft:jungle_log", "position": {"x": -164, "y": 73, "z": 51}},
                {"block_id": "minecraft:oak_log", "position": {"x": -169, "y": 72, "z": 58}},
            ],
        }
    )
    first = strategy.propose(state, observation)
    assert first.parameters == {"block_type": "any_log", "count": 4}
    state = strategy.accept_result(state, {})
    mixed = observation.model_copy(update={"inventory": {"jungle_log": 4, "oak_log": 4}})
    assert inventory_resource_count(mixed, "any_log") == 8
    second = strategy.propose(state, mixed)
    assert second.capability == "craft"
    assert second.parameters == {"recipe": "any_planks", "count": 32}
    enough = mixed.model_copy(update={"inventory": {"jungle_log": 4, "oak_log": 8}})
    craft = strategy.propose(state, enough)
    assert craft.parameters == {"recipe": "any_planks", "count": 32}
    assert state["workflow"].adaptive_wood is False
    assert workflow.steps[0].parameters == {"block_type": "oak_log", "count": 8}
    assert [s.maximum_cost for s in state["workflow"].steps] == [
        s.maximum_cost for s in workflow.steps
    ]


def test_partial_mixed_wood_growth_is_recoverable_before_total_recipe_stock():
    mission = build_nether_portal_mission(mission_id="partial-mixed-wood-progress")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    )
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(mission.objectives[0].goal)
    before = Observation.model_validate({**MESSAGES["Observation"], "inventory": {"jungle_log": 4}})
    strategy.propose(state, before)
    after = before.model_copy(update={"inventory": {"jungle_log": 4, "minecraft:oak_log": 2}})
    assert inventory_resource_count(after, "any_log") == 6
    assert strategy.accept_partial_result(state, before, after) is not None
    assert strategy.propose(state, after).parameters == {"block_type": "any_log", "count": 2}
    saplings = before.model_copy(update={"inventory": {"jungle_log": 4, "oak_sapling": 2}})
    assert strategy.accept_partial_result(state, before, saplings) is None
    duplicate = before.model_copy(
        update={"inventory": {"jungle_log": 4, "minecraft:jungle_log": 4}}
    )
    assert strategy.accept_partial_result(state, before, duplicate) is None


def test_r106_mixed_stock_advances_without_spending_another_search_action():
    mission = build_nether_portal_mission(mission_id="r106-mixed-stock", home=(0, 64, 0))
    workflow = next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    registry = WorkflowRegistry()
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(mission.objectives[0].goal)
    limit = mission.budget.model_copy(update=mission.objectives[0].budget.model_dump())
    spent = BudgetUsage(
        max_actions=2, max_blocks_changed=16, max_travel_distance=128.14538949888098
    )
    account = BudgetAccount(limit=limit).reserve("first-two", spent).settle("first-two", spent)
    state["budget_remaining"] = account.remaining
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"inventory": {"oak_log": 5, "spruce_log": 3}}
    )
    before = account.remaining
    decision = strategy.propose(state, observation)
    assert decision.capability == "craft"
    assert decision.parameters == {"recipe": "any_planks", "count": 32}
    assert account.remaining == before and account.limit == limit
    assert limit.max_actions == 16 and limit.max_blocks_changed == 256
    assert [s.maximum_cost for s in state["workflow"].steps] == [
        s.maximum_cost for s in workflow.steps
    ]
    assert workflow.steps[0].parameters["block_type"] == "oak_log"
    planks = observation.model_copy(update={"inventory": {"oak_planks": 20, "spruce_planks": 12}})
    assert inventory_resource_count(planks, "any_planks") == 32


def test_workstation_reservations_fit_unchanged_iron_budget_and_leave_a_local_table() -> None:
    mission = build_nether_portal_mission(mission_id="workstations", home=(0, 64, 0))
    registry = WorkflowRegistry()
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    iron, pickaxe = mission.objectives[:2]
    workflow = registry.resolve(iron.goal)
    assert workflow is not None
    assert iron.budget.max_travel_distance == 512
    assert iron.budget.max_blocks_changed == 256
    assert pickaxe.budget.max_travel_distance == pickaxe.budget.max_blocks_changed == 0
    assert len(mission.objectives) == 9
    assert [step.capability for step in workflow.steps[-3:]] == ["collect", "craft", "smelt"]
    assert workflow.steps[-2].parameters["recipe"] == "furnace"
    for step in workflow.steps:
        if step.capability == "smelt" or step.parameters.get("recipe") in {
            "wooden_pickaxe",
            "stone_pickaxe",
            "furnace",
        }:
            assert step.maximum_cost.max_blocks_changed == 8
            assert step.maximum_cost.max_travel_distance == 8
    assert sum(step.maximum_cost.max_travel_distance for step in workflow.steps) == 512
    water = registry.resolve(mission.objectives[3].goal)
    assert water is not None and water.target == "water_bucket"
    assert sum(step.maximum_cost.max_travel_distance for step in water.steps) == 128


@pytest.mark.parametrize("raw_iron", [0, 2, 6, 7])
def test_iron_kit_collects_successful_small_batches_before_smelting_seven(raw_iron: int) -> None:
    mission = build_nether_portal_mission(mission_id="iron-batches")
    registry = WorkflowRegistry()
    workflow = next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "inventory": {"stone_pickaxe": 1, "furnace": 1, "oak_planks": 7, "raw_iron": raw_iron}
        }
    )
    account = BudgetAccount(
        limit=mission.budget.model_copy(update=mission.objectives[0].budget.model_dump())
    )
    count = 0
    for stock in range(raw_iron, 7):
        decision = strategy.propose(state, observation)
        assert decision.kind == "execute" and decision.capability == "collect"
        assert decision.parameters == {"block_type": "iron_ore", "count": 1}
        assert decision.maximum_cost == workflow.steps[7].maximum_cost
        count += 1
        account = account.reserve(str(stock), decision.maximum_cost).settle(
            str(stock), BudgetUsage(max_actions=1, max_blocks_changed=1, max_travel_distance=10)
        )
        state = strategy.accept_result(state, {})
        observation = observation.model_copy(
            update={"inventory": {**observation.inventory, "raw_iron": stock + 1}}
        )
    decision = strategy.propose(state, observation)
    assert decision.kind == "execute" and decision.capability == "smelt"
    assert decision.parameters == {"item": "raw_iron", "fuel": "any_planks", "count": 7}
    assert count == 7 - raw_iron
    assert account.used.max_actions == count
    assert len(workflow.steps) == 10
    assert len(workflow.steps) - 1 + 7 == mission.objectives[0].budget.max_actions == 16
    assert sum(step.maximum_cost.max_travel_distance for step in workflow.steps) == 512
    state = strategy.accept_result(state, {})
    final = observation.model_copy(update={"inventory": {"iron_ingot": 7}})
    assert strategy.propose(state, final).kind == "complete"


def test_iron_batches_keep_the_existing_command_account_and_per_call_limits() -> None:
    mission = build_nether_portal_mission(mission_id="iron-account")
    workflow = next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    ore = workflow.steps[7]
    limit = mission.budget.model_copy(update=mission.objectives[0].budget.model_dump())
    # A controlled accounting case, not a prediction or replay of a new native route.
    used = BudgetUsage(max_actions=8, max_blocks_changed=41, max_travel_distance=265.4591884092872)
    account = BudgetAccount(limit=limit, used=used)
    assert ore.maximum_cost.max_travel_distance == ore.maximum_cost.max_blocks_changed == 192
    settled = account.reserve("last-ore", ore.maximum_cost).settle("last-ore", ore.maximum_cost)
    assert settled.limit == limit
    assert settled.used.max_actions == 9
    assert settled.used.max_travel_distance == used.max_travel_distance + 192
    assert settled.used.max_blocks_changed == 233
    with pytest.raises(ValueError):
        settled.reserve("cannot-reset-the-account", ore.maximum_cost)


@pytest.mark.parametrize("wrapped", [False, True])
def test_iron_batch_reservation_uses_current_account_and_preserves_remaining_work(
    wrapped: bool,
) -> None:
    from animetta.tools.minecraft.voyager.strategies.mission import MissionStrategy

    mission = build_nether_portal_mission(mission_id="remaining-iron")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    )
    fallback = FallbackStrategy(registry=registry)
    strategy = MissionStrategy(live=None, learn=None, fallback=fallback) if wrapped else fallback
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "inventory": {"stone_pickaxe": 1, "oak_planks": 23, "cobblestone": 40, "raw_iron": 1}
        }
    )
    limit = mission.budget.model_copy(update=mission.objectives[0].budget.model_dump())
    # R59 settled usage: the next batch must fit 167 blocks rather than request 192.
    account = BudgetAccount(
        limit=limit,
        used=BudgetUsage(
            max_actions=8, max_blocks_changed=89, max_travel_distance=63.67350095384333
        ),
    )
    for stock in range(1, 7):
        state["budget_remaining"] = account.remaining
        decision = strategy.propose(state, observation)
        assert decision.kind == "execute" and decision.parameters == {
            "block_type": "iron_ore",
            "count": 1,
        }
        # Keep both workstation ceilings and one mutation per still-needed later ore.
        assert (
            3
            <= decision.maximum_cost.max_blocks_changed
            <= account.remaining.max_blocks_changed - 16 - (6 - stock)
        )
        assert decision.maximum_cost.max_blocks_changed <= 192
        assert decision.maximum_cost.max_travel_distance <= min(
            192, account.remaining.max_travel_distance - 16
        )
        actual_blocks = decision.maximum_cost.max_blocks_changed - 2 if stock == 1 else 1
        account = account.reserve(str(stock), decision.maximum_cost).settle(
            str(stock), BudgetUsage(max_actions=1, max_blocks_changed=actual_blocks)
        )
        state = strategy.accept_result(state, {})
        observation = observation.model_copy(
            update={"inventory": {**observation.inventory, "raw_iron": stock + 1}}
        )
    for recipe in ("furnace", "smelt"):
        state["budget_remaining"] = account.remaining
        decision = strategy.propose(state, observation)
        assert decision.capability == ("craft" if recipe == "furnace" else "smelt")
        account = account.reserve(recipe, decision.maximum_cost).settle(
            recipe, BudgetUsage(max_actions=1, max_blocks_changed=3)
        )
        state = strategy.accept_result(state, {})
        inventory = {**observation.inventory, "furnace": 1}
        if recipe == "smelt":
            inventory.update(raw_iron=0, iron_ingot=7)
        observation = observation.model_copy(update={"inventory": inventory})
    assert strategy.propose(state, observation).kind == "complete"
    assert account.limit == limit
    assert account.used.max_actions == limit.max_actions == 16
    assert account.used.max_blocks_changed <= limit.max_blocks_changed == 256


@pytest.mark.parametrize(
    "remaining_override",
    [{"max_blocks_changed": 17}, {"max_actions": 2}, {"max_travel_distance": 15}],
)
def test_iron_batch_rejects_budget_that_cannot_cover_the_remaining_goal(
    remaining_override: dict[str, int],
) -> None:
    mission = build_nether_portal_mission(mission_id="insufficient-iron")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    )
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(mission.objectives[0].goal)
    state["budget_remaining"] = mission.budget.model_copy(
        update={**mission.objectives[0].budget.model_dump(), **remaining_override}
    )
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"inventory": {"stone_pickaxe": 1, "oak_planks": 23, "raw_iron": 1}}
    )
    decision = strategy.propose(state, observation)
    assert decision.kind == "failure" and decision.code == "BUDGET_EXHAUSTED"


def test_a_settled_failed_search_is_paid_for_by_packing_work_inside_the_same_iron_budget():
    mission = build_nether_portal_mission(mission_id="recovery-packed-iron")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    )
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(mission.objectives[0].goal)
    limit = mission.budget.model_copy(update=mission.objectives[0].budget.model_dump())
    # One previously failed native search is included, never discarded or refunded.
    account = BudgetAccount(
        limit=limit,
        used=BudgetUsage(max_actions=9, max_blocks_changed=89, max_travel_distance=174.94),
    )
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "inventory": {"stone_pickaxe": 1, "oak_planks": 23, "cobblestone": 40, "raw_iron": 1},
        }
    )
    batches = []
    while observation.inventory["raw_iron"] < 7:
        state["budget_remaining"] = account.remaining
        decision = strategy.propose(state, observation)
        assert decision.capability == "collect"
        count = decision.parameters["count"]
        batches.append(count)
        assert 1 <= count <= 7 - observation.inventory["raw_iron"]
        assert decision.maximum_cost.max_actions == 1
        assert decision.maximum_cost.max_blocks_changed <= 192
        assert decision.maximum_cost.max_travel_distance <= 192
        account = account.reserve(f"batch-{len(batches)}", decision.maximum_cost).settle(
            f"batch-{len(batches)}", BudgetUsage(max_actions=1, max_blocks_changed=count)
        )
        state = strategy.accept_result(state, {})
        observation = observation.model_copy(
            update={
                "inventory": {
                    **observation.inventory,
                    "raw_iron": observation.inventory["raw_iron"] + count,
                }
            }
        )
    assert batches == [2, 1, 1, 1, 1]
    for capability in ("craft", "smelt"):
        state["budget_remaining"] = account.remaining
        decision = strategy.propose(state, observation)
        assert decision.capability == capability
        account = account.reserve(capability, decision.maximum_cost).settle(
            capability, BudgetUsage(max_actions=1, max_blocks_changed=3)
        )
        state = strategy.accept_result(state, {})
        inventory = {**observation.inventory, "furnace": 1}
        if capability == "smelt":
            inventory.update(raw_iron=0, iron_ingot=7)
        observation = observation.model_copy(update={"inventory": inventory})
    assert strategy.propose(state, observation).kind == "complete"
    assert GoalVerifier().verify(goal=mission.objectives[0].goal, final=observation)["satisfied"]
    assert account.limit == limit
    assert account.used.max_actions == limit.max_actions == 16
    assert account.used.max_blocks_changed <= limit.max_blocks_changed == 256
    assert account.used.max_travel_distance == 174.94 < limit.max_travel_distance


def test_iron_kit_skips_remaining_batches_when_seven_ingots_are_observed() -> None:
    mission = build_nether_portal_mission(mission_id="iron-already-smelted")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    )
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(mission.objectives[0].goal)
    state["step_index"] = 7
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"inventory": {"iron_ingot": 7}}
    )
    assert strategy.propose(state, observation).kind == "complete"


@pytest.mark.parametrize("wood", ["spruce", "birch", "dark_oak", "mangrove", "cherry"])
def test_wood_bootstrap_uses_native_family_recipes_for_observed_species(wood: str) -> None:
    workflow = next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    registry = WorkflowRegistry()
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    mission = build_nether_portal_mission(mission_id="observed-wood")
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "inventory": {},
            "position": {"x": -48, "y": 68, "z": -193},
            "visible_blocks": [
                {"block_id": f"minecraft:{wood}_log", "position": {"x": -51, "y": 68, "z": -196}}
            ],
        }
    )

    first = strategy.propose(state, observation)
    assert first.parameters == {"block_type": "any_log", "count": 8}
    assert first.maximum_cost == workflow.steps[0].maximum_cost
    assert state["workflow"].adaptive_wood is False
    state = strategy.accept_result(state, {})
    second = strategy.propose(
        state, observation.model_copy(update={"inventory": {f"{wood}_log": 8}})
    )
    assert second.parameters == {"recipe": "any_planks", "count": 32}
    bound = state["workflow"]
    assert bound.steps[1].parameters == {"recipe": "any_planks", "count": 32}
    assert bound.steps[-1].parameters["fuel"] == "any_planks"
    assert bound.collection_targets[0].item == "any_log"
    assert bound.checkpoints[0].any_of[0].inventory_all[1].item == "any_planks"
    assert [s.maximum_cost for s in bound.steps] == [s.maximum_cost for s in workflow.steps]
    # Registered templates stay exact and reusable by a different command.
    assert workflow.steps[0].parameters["block_type"] == "oak_log"
    assert bound.adaptive_wood is False


def test_wood_bootstrap_keeps_carried_progress_without_binding_a_recipe_early() -> None:
    workflow = next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    registry = WorkflowRegistry()
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    mission = build_nether_portal_mission(mission_id="carried-wood")
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "inventory": {"minecraft:birch_log": 4},
            "visible_blocks": [
                {"block_id": "minecraft:spruce_log", "position": {"x": 0, "y": 64, "z": 0}}
            ],
        }
    )
    decision = strategy.propose(state, observation)
    assert decision.parameters == {"block_type": "any_log", "count": 4}
    after = observation.model_copy(update={"inventory": {"birch_log": 5}})
    assert strategy.accept_partial_result(state, observation, after) is not None


def test_visible_logs_do_not_lock_recipes_and_nonadaptive_workflows_stay_exact() -> None:
    workflow = next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    registry = WorkflowRegistry()
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    goal = build_nether_portal_mission(mission_id="nearest-wood").objectives[0].goal
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "inventory": {},
            "position": {"x": 0, "y": 64, "z": 0},
            "visible_blocks": [
                {"block_id": "minecraft:oak_log", "position": {"x": 20, "y": 64, "z": 0}},
                {"block_id": "minecraft:birch_leaves", "position": {"x": 1, "y": 64, "z": 0}},
                {"block_id": "minecraft:spruce_log", "position": {"x": 3, "y": 64, "z": 0}},
            ],
        }
    )
    assert (
        strategy.propose(strategy.prepare(goal), observation).parameters["block_type"] == "any_log"
    )
    exact = WorkflowDefinition(
        workflow_id="exact:oak", intent=goal.intent, target=goal.target, steps=workflow.steps[:1]
    )
    exact_registry = WorkflowRegistry()
    exact_registry.register(exact)
    exact_strategy = FallbackStrategy(registry=exact_registry)
    assert (
        exact_strategy.propose(exact_strategy.prepare(goal), observation).parameters["block_type"]
        == "oak_log"
    )


def test_mainline_fits_finite_mission_authority_and_workflow_reservations() -> None:
    mission = build_nether_portal_mission(mission_id="survival-budget", home=(0, 64, 0))
    policy = _budget_policy(MinecraftConfig())
    authorized = effective_budget(
        RequestedBudget.model_validate(mission.budget.model_dump()),
        policy.mission.model_copy(
            update={"resource_consumption": mission.budget.resource_consumption}
        ),
    )
    type(mission).model_validate({**mission.model_dump(), "budget": authorized})
    assert mission.budget.max_travel_distance <= 2_000
    assert policy.learn.max_travel_distance == 500
    registry = WorkflowRegistry()
    from animetta.tools.minecraft.survival.workflows import iron_survival_workflow

    registry.register(iron_survival_workflow())
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    for objective in mission.objectives:
        workflow = registry.resolve(objective.goal)
        if workflow is not None:
            # Sequential conservative reservations are not spent simultaneously;
            # each step must individually fit the objective budget.
            assert all(
                step.maximum_cost.max_travel_distance <= objective.budget.max_travel_distance
                for step in workflow.steps
            )
            assert all(
                step.maximum_cost.max_blocks_changed <= objective.budget.max_blocks_changed
                for step in workflow.steps
            )


def test_mainline_orders_dependencies_and_resolves_prerequisites() -> None:
    mission = build_nether_portal_mission(mission_id="survival-portal-test")
    registry = WorkflowRegistry()
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    observation = Observation.model_validate(MESSAGES["Observation"])
    for index, objective in enumerate(mission.objectives):
        assert objective.dependencies == (
            (mission.objectives[index - 1].objective_id,) if index else ()
        )
        if objective.objective_id in {
            "iron",
            "iron-pickaxe",
            "water-bucket",
            "diamond-pickaxe",
            "ignition",
            "obsidian",
        }:
            assert registry.resolve(objective.goal) is not None
            strategy = FallbackStrategy(registry=registry)
            assert strategy.propose(strategy.prepare(objective.goal), observation).kind == "execute"


def test_obsidian_reservation_covers_real_multi_dig_backfill_receipt() -> None:
    mission = build_nether_portal_mission(
        mission_id="obsidian-partial-drops", resume_from="obsidian"
    )
    workflow = next(item for item in nether_preparation_workflows() if item.target == "obsidian")
    collection = workflow.steps[1]
    account = BudgetAccount(limit=mission.budget).reserve("collect", collection.maximum_cost)
    # A real one-item collection needed three digs and three verified backfills.
    settled = account.settle(
        "collect",
        BudgetUsage(max_actions=1, max_blocks_changed=6, max_travel_distance=16.28),
    )
    assert settled.used.max_blocks_changed == 6
    assert collection.maximum_cost.max_blocks_changed >= 4 * 2
    assert mission.objectives[0].budget.max_blocks_changed >= sum(
        step.maximum_cost.max_blocks_changed for step in workflow.steps
    )


def test_stone_preparation_cost_and_inventory_resume_cover_real_retry8_receipt() -> None:
    mission = build_nether_portal_mission(mission_id="stone-preparation-resume")
    registry = WorkflowRegistry()
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    workflow = registry.resolve(mission.objectives[0].goal)
    assert workflow is not None
    stone = workflow.steps[5]
    assert stone.maximum_cost.max_blocks_changed >= 47
    assert stone.maximum_cost.max_travel_distance >= 56.48043503820463
    # Iron collection also owns the shaft from the surface down to Y16.
    iron = next(step for step in workflow.steps if step.parameters.get("block_type") == "iron_ore")
    assert iron.maximum_cost.max_blocks_changed >= (64 - 16) * 3 + 7
    assert mission.objectives[0].budget.max_blocks_changed >= (
        workflow.steps[0].maximum_cost.max_blocks_changed
        + 47
        + iron.maximum_cost.max_blocks_changed
    )
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "inventory": {
                "crafting_table": 1,
                "wooden_pickaxe": 1,
                "oak_planks": 23,
                "stick": 2,
                "cobblestone": 40,
            },
        }
    )
    strategy = FallbackStrategy(registry=registry)
    decision = strategy.propose(strategy.prepare(mission.objectives[0].goal), observation)
    assert decision.kind == "execute"
    assert decision.capability == "craft"
    assert decision.parameters == {"recipe": "stone_pickaxe", "count": 1}


def test_wood_collection_reservation_covers_real_retry10_and_resumes_from_logs() -> None:
    mission = build_nether_portal_mission(mission_id="wood-resume")
    registry = WorkflowRegistry()
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    workflow = registry.resolve(mission.objectives[0].goal)
    assert workflow is not None
    assert workflow.steps[0].maximum_cost.max_travel_distance >= 175.36448964869066
    assert workflow.steps[0].maximum_cost.max_blocks_changed >= 12
    assert (
        sum(step.maximum_cost.max_travel_distance for step in workflow.steps)
        <= mission.objectives[0].budget.max_travel_distance
    )
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "inventory": {"oak_log": 10, "stick": 1, "oak_sapling": 2},
        }
    )
    strategy = FallbackStrategy(registry=registry)
    decision = strategy.propose(strategy.prepare(mission.objectives[0].goal), observation)
    assert decision.kind == "execute"
    assert decision.capability == "craft"
    assert decision.parameters == {"recipe": "any_planks", "count": 32}


def test_mainline_resume_from_obsidian_keeps_suffix_and_recomputes_budget() -> None:
    mission = build_nether_portal_mission(
        mission_id="survival-resume-obsidian", home=(0, 64, 0), resume_from="obsidian"
    )
    assert [objective.objective_id for objective in mission.objectives] == [
        "obsidian",
        "return-home",
        "portal",
    ]
    assert mission.objectives[0].dependencies == ()
    assert mission.objectives[1].dependencies == ("obsidian",)
    assert mission.objectives[2].dependencies == ("return-home",)
    assert mission.budget.max_actions == 44
    assert mission.budget.max_strategy_attempts == 3
    assert mission.budget.max_travel_distance == 640
    assert mission.budget.max_blocks_changed == 376
    assert mission.budget.max_damage_taken == 3
    assert mission.budget.resource_consumption == {
        "minecraft:obsidian": 10,
        "minecraft:cobbled_deepslate": 4,
    }


def test_mainline_resume_portal_only_keeps_obsidian_resource_reservation() -> None:
    mission = build_nether_portal_mission(mission_id="survival-resume-portal", resume_from="portal")
    assert [objective.objective_id for objective in mission.objectives] == ["portal"]
    assert mission.objectives[0].dependencies == ()
    assert mission.objectives[0].budget.resource_consumption == {
        "minecraft:obsidian": 10,
        "minecraft:cobbled_deepslate": 4,
    }
    assert mission.budget.max_actions == 20
    assert mission.budget.max_travel_distance == 128
    assert mission.budget.resource_consumption == {
        "minecraft:obsidian": 10,
        "minecraft:cobbled_deepslate": 4,
    }


def test_mainline_default_resume_keeps_full_chain_and_total_budget() -> None:
    mission = build_nether_portal_mission(mission_id="survival-full-chain", home=(0, 64, 0))
    assert mission == build_nether_portal_mission(
        mission_id="survival-full-chain", home=(0, 64, 0), resume_from="iron"
    )
    assert [objective.objective_id for objective in mission.objectives] == [
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
    assert mission.objectives[0].dependencies == ()
    assert mission.budget.max_travel_distance == 1_984
    assert mission.budget.max_damage_taken == 9
    assert mission.budget.max_blocks_changed == 1088


def test_water_preparation_reserves_iron_before_deep_mining() -> None:
    mission = build_nether_portal_mission(mission_id="safe-obsidian")
    iron, iron_pickaxe, water, ignition, pickaxe, obsidian, _ = mission.objectives
    assert iron.goal.target == "nether_iron_kit"
    iron_threshold = iron.goal.success_predicates[0]
    from animetta.tools.minecraft.voyager.goal_models import InventoryAtLeast

    assert isinstance(iron_threshold, InventoryAtLeast)
    assert iron_threshold.item == "iron_ingot"
    assert iron_threshold.quantity == 7  # bucket3 + steel1 + iron pickaxe3
    assert iron_pickaxe.dependencies == (iron.objective_id,)
    assert water.dependencies == (iron_pickaxe.objective_id,)
    assert ignition.dependencies == (water.objective_id,)
    assert pickaxe.dependencies == (ignition.objective_id,)
    registry = WorkflowRegistry()
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    kit = registry.resolve(iron.goal)
    assert kit is not None
    ore_index = next(
        i for i, step in enumerate(kit.steps) if step.parameters.get("block_type") == "iron_ore"
    )
    assert kit.steps[ore_index].parameters["count"] == 1
    raw_threshold = kit.collection_targets[ore_index]
    assert raw_threshold is not None and raw_threshold.quantity == 7
    water_workflow = registry.resolve(water.goal)
    assert water_workflow is not None
    assert [step.capability for step in water_workflow.steps] == ["craft", "fill_water_bucket"]
    assert water_workflow.steps[-1].maximum_cost.max_blocks_changed == 1
    obsidian_workflow = registry.resolve(obsidian.goal)
    assert obsidian_workflow is not None
    assert obsidian_workflow.steps[0].capability == "prepare_obsidian"
    ignition_workflow = registry.resolve(ignition.goal)
    assert ignition_workflow is not None
    flint = next(step for step in ignition_workflow.steps if step.capability == "acquire_flint")
    attempts = flint.parameters["max_attempts"]
    assert isinstance(attempts, int)
    assert flint.maximum_cost.max_blocks_changed >= 2 * attempts + 3


def test_iron_pickaxe_is_crafted_before_underground_return_without_replaying_iron() -> None:
    mission = build_nether_portal_mission(
        mission_id="tool-maintenance", home=(11, 64, 75), resume_from="iron-pickaxe"
    )
    objective, travel = mission.objectives[:2]
    assert objective.objective_id == "iron-pickaxe"
    assert objective.dependencies == ()
    assert travel.objective_id == "water-return"
    assert travel.dependencies == (objective.objective_id,)
    registry = WorkflowRegistry()
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"inventory": {"iron_ingot": 7, "stick": 3, "crafting_table": 1}}
    )
    decision = strategy.propose(strategy.prepare(objective.goal), observation)
    assert decision.kind == "execute"
    assert decision.capability == "craft"
    assert decision.parameters == {"recipe": "iron_pickaxe", "count": 1}
    already_equipped = observation.model_copy(update={"inventory": {"iron_pickaxe": 1}})
    assert strategy.propose(strategy.prepare(objective.goal), already_equipped).kind == "complete"


def test_two_diamonds_keep_three_diamond_descent_and_prepare_spare_pickaxes() -> None:
    mission = build_nether_portal_mission(
        mission_id="finish-diamonds", resume_from="diamond-pickaxe"
    )
    registry = WorkflowRegistry()
    for workflow in nether_preparation_workflows():
        registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "position": {"x": 9, "y": -22, "z": 79},
            "inventory": {"diamond": 2, "iron_pickaxe": 1, "cobblestone": 39, "stick": 1},
        }
    )
    goal = mission.objectives[0].goal
    sticks = strategy.propose(strategy.prepare(goal), observation)
    assert sticks.kind == "execute"
    assert sticks.parameters == {"recipe": "stick", "count": 8}
    with_sticks = observation.model_copy(
        update={"inventory": {**observation.inventory, "stick": 9}}
    )
    spares = strategy.propose(strategy.prepare(goal), with_sticks)
    assert spares.kind == "execute"
    assert spares.parameters == {"recipe": "stone_pickaxe", "count": 2}
    equipped = with_sticks.model_copy(
        update={"inventory": {**with_sticks.inventory, "stone_pickaxe": 2, "stick": 5}}
    )
    descent = strategy.propose(strategy.prepare(goal), equipped)
    assert descent.kind == "execute"
    assert descent.parameters == {"target_y": -24, "minimum_cobblestone": 0}
    enough = observation.model_copy(update={"inventory": {"diamond": 3, "stick": 2}})
    craft = strategy.propose(strategy.prepare(goal), enough)
    assert craft.kind == "execute"
    assert craft.parameters == {"recipe": "diamond_pickaxe", "count": 1}


@pytest.mark.parametrize("diamond_stock", [0, 2])
def test_diamond_search_uses_unspent_command_blocks_and_keeps_the_pickaxe_reservation(
    diamond_stock: int,
) -> None:
    mission = build_nether_portal_mission(mission_id="diamond-search-reservation")
    objective = next(o for o in mission.objectives if o.objective_id == "diamond-pickaxe")
    workflow = next(w for w in nether_preparation_workflows() if w.target == "diamond_pickaxe")
    registry = WorkflowRegistry()
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(objective.goal)
    limit = mission.budget.model_copy(update=objective.budget.model_dump())
    # R77 reached -54 with 100/256 blocks spent. The old three-block
    # reservation expired on tuff before the native preparation reached -58.
    account = BudgetAccount(
        limit=limit,
        used=BudgetUsage(max_actions=14, max_blocks_changed=100, max_travel_distance=97.45877),
    )
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "position": {"x": 1, "y": -54, "z": 54},
            "inventory": {
                "iron_pickaxe": 1,
                "stone_pickaxe": 3,
                "stick": 4,
                "cobblestone": 162,
                "diamond": diamond_stock,
            },
        }
    )
    state["budget_remaining"] = account.remaining
    collect = strategy.propose(state, observation)
    assert collect.capability == "collect"
    assert collect.parameters == {"block_type": "diamond_ore", "count": 3 - diamond_stock}
    assert collect.maximum_cost.max_blocks_changed == 148
    assert collect.maximum_cost.max_travel_distance == 256
    assert workflow.steps[state["step_index"]].maximum_cost.max_blocks_changed == 3
    # Charge both necessary preparation and ore extraction to this same account.
    account = account.reserve("diamonds", collect.maximum_cost).settle(
        "diamonds", BudgetUsage(max_actions=1, max_blocks_changed=4 + 3 - diamond_stock)
    )
    state = strategy.accept_result(state, {})
    observation = observation.model_copy(
        update={"inventory": {**observation.inventory, "diamond": 3}}
    )
    state["budget_remaining"] = account.remaining
    craft = strategy.propose(state, observation)
    assert craft.parameters == {"recipe": "diamond_pickaxe", "count": 1}
    assert craft.maximum_cost.max_blocks_changed == 8
    account = account.reserve("pickaxe", craft.maximum_cost).settle(
        "pickaxe", BudgetUsage(max_actions=1, max_blocks_changed=1)
    )
    final = observation.model_copy(update={"inventory": {"diamond_pickaxe": 1}})
    assert GoalVerifier().verify(goal=objective.goal, final=final)["satisfied"]
    assert account.limit == limit and limit.max_blocks_changed == 256
    assert limit.max_actions == 40 and limit.max_travel_distance == 384
    assert account.used.max_blocks_changed <= 108


@pytest.mark.parametrize(
    "spent", [{"max_blocks_changed": 244}, {"max_actions": 39}, {"max_travel_distance": 377}]
)
def test_diamond_search_cannot_borrow_the_stopping_or_future_work_budget(spent) -> None:
    mission = build_nether_portal_mission(mission_id="diamond-search-no-budget")
    objective = next(o for o in mission.objectives if o.objective_id == "diamond-pickaxe")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "diamond_pickaxe")
    )
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(objective.goal)
    account = BudgetAccount(
        limit=mission.budget.model_copy(update=objective.budget.model_dump()),
        used=BudgetUsage(**spent),
    )
    state["budget_remaining"] = account.remaining
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "position": {"x": 1, "y": -54, "z": 54},
            "inventory": {"iron_pickaxe": 1, "stone_pickaxe": 3, "stick": 4},
        }
    )
    decision = strategy.propose(state, observation)
    assert decision.kind == "failure" and decision.code == "BUDGET_EXHAUSTED"


@pytest.mark.parametrize("wood", ["birch", "any"])
def test_ignition_reallocates_ore_budget_but_rejects_unaffordable_cold_chain(wood):
    mission = build_nether_portal_mission(mission_id="ignition-search-reservation")
    objective = next(o for o in mission.objectives if o.goal.target == "flint_and_steel")
    workflow = next(w for w in nether_preparation_workflows() if w.target == "flint_and_steel")
    registry = WorkflowRegistry()
    registry.register(workflow)
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(objective.goal)
    account = BudgetAccount(limit=mission.budget.model_copy(update=objective.budget.model_dump()))
    state["budget_remaining"] = account.remaining
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "inventory": {},
            "visible_blocks": []
            if wood == "any"
            else [{"block_id": "minecraft:birch_log", "position": {"x": 1, "y": 64, "z": 1}}],
        }
    )
    logs = strategy.propose(state, observation)
    # The original 128 travel cannot reserve the complete cold chain's 136
    # future travel. Do not enlarge it just to make this standalone case run.
    assert logs.kind == "failure" and logs.code == "BUDGET_EXHAUSTED"
    assert state["workflow"].shared_collection_budget_items == ("any_log", "raw_iron")
    observation = observation.model_copy(update={"inventory": {"birch_planks": 8}})
    state["budget_remaining"] = account.remaining
    ore = strategy.propose(state, observation)
    assert ore.parameters == {"block_type": "iron_ore", "count": 1}
    assert ore.maximum_cost.max_blocks_changed == 8
    assert ore.maximum_cost.max_travel_distance == 56
    assert account.limit.max_blocks_changed == 64
    assert account.limit.max_travel_distance == 128
    assert workflow.steps[0].maximum_cost.max_blocks_changed == 2
    assert workflow.steps[2].maximum_cost.max_blocks_changed == 1


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize(
    "spent_blocks,spent_travel,first_blocks,first_travel,next_blocks,next_travel",
    [
        (238, 100, 18, 24, 10, 24),
        (100, 370, 24, 14, 24, 8),
        (100, 100, 24, 24, 24, 24),
    ],
)
def test_depth_reservations_fit_the_current_original_account_after_partial_progress(
    wrapped, spent_blocks, spent_travel, first_blocks, first_travel, next_blocks, next_travel
):
    from animetta.tools.minecraft.voyager.strategies.mission import MissionStrategy

    mission = build_nether_portal_mission(mission_id="depth-reservation-frontier")
    objective = next(o for o in mission.objectives if o.objective_id == "diamond-pickaxe")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "diamond_pickaxe")
    )
    fallback = FallbackStrategy(registry=registry)
    strategy = MissionStrategy(live=None, learn=None, fallback=fallback) if wrapped else fallback
    state = strategy.prepare(objective.goal)
    limit = mission.budget.model_copy(update=objective.budget.model_dump())
    account = BudgetAccount(
        limit=limit,
        used=BudgetUsage(
            max_actions=18, max_blocks_changed=spent_blocks, max_travel_distance=spent_travel
        ),
    )
    before = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "position": {"x": 448, "y": -40, "z": 285},
            "inventory": {
                "iron_pickaxe": 1,
                "stone_pickaxe": 2,
                "stick": 8,
                "oak_planks": 12,
                "crafting_table": 1,
            },
        }
    )
    state["budget_remaining"] = account.remaining
    first = strategy.propose(state, before)
    assert first.parameters == {"target_y": -48, "minimum_cobblestone": 0}
    assert first.maximum_cost.max_blocks_changed == first_blocks
    assert first.maximum_cost.max_travel_distance == first_travel
    delegate = state["strategy_state"] if wrapped else state
    index = delegate["step_index"]
    # Reservation and runtime settlement share this same bounded maximum.
    account = account.reserve("frontier", first.maximum_cost).settle(
        "frontier", BudgetUsage(max_actions=1, max_blocks_changed=8, max_travel_distance=6)
    )
    after = before.model_copy(update={"position": before.position.model_copy(update={"y": -46})})
    recovered = strategy.accept_partial_result(state, before, after)
    assert recovered is not None
    recovered["budget_remaining"] = account.remaining
    second = strategy.propose(recovered, after)
    assert second.parameters == first.parameters
    assert second.maximum_cost.max_blocks_changed == next_blocks
    assert second.maximum_cost.max_travel_distance == next_travel
    account.reserve("next-frontier", second.maximum_cost)
    delegate = recovered["strategy_state"] if wrapped else recovered
    assert delegate["step_index"] == index
    assert delegate["workflow"].steps[index].maximum_cost.max_blocks_changed == 24
    assert account.used.max_blocks_changed == spent_blocks + 8
    assert account.used.max_travel_distance == spent_travel + 6
    assert account.used.max_actions == 19
    assert account.limit == limit and limit.max_blocks_changed == 256
    assert recovered["goal"] == objective.goal


@pytest.mark.parametrize("wrapped", [False, True])
def test_partial_shaft_depth_resumes_the_same_checkpoint_in_the_original_charged_account(wrapped):
    from animetta.tools.minecraft.voyager.strategies.mission import MissionStrategy

    mission = build_nether_portal_mission(mission_id="partial-shaft-depth")
    objective = next(o for o in mission.objectives if o.objective_id == "diamond-pickaxe")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "diamond_pickaxe")
    )
    fallback = FallbackStrategy(registry=registry)
    strategy = MissionStrategy(live=None, learn=None, fallback=fallback) if wrapped else fallback
    state = strategy.prepare(objective.goal)
    limit = mission.budget.model_copy(update=objective.budget.model_dump())
    account = BudgetAccount(
        limit=limit,
        used=BudgetUsage(
            max_actions=12,
            max_blocks_changed=96,
            max_travel_distance=76,
        ),
    )
    state["budget_remaining"] = account.remaining
    before = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "position": {"x": -18, "y": -24, "z": 22},
            "inventory": {"iron_pickaxe": 1, "stone_pickaxe": 2, "stick": 4, "cobblestone": 40},
        }
    )
    step = strategy.propose(state, before)
    assert step.parameters == {"minimum_cobblestone": 0, "target_y": -32}
    assert step.maximum_cost.max_blocks_changed == 24
    delegate = state["strategy_state"] if wrapped else state
    index = delegate["step_index"]
    # R82 exhausted this local allowance while descending -24 -> -29. All24
    # mutations remain charged against the unchanged256-block command limit.
    account = account.reserve("partial", step.maximum_cost).settle(
        "partial",
        BudgetUsage(max_actions=1, max_blocks_changed=24, max_travel_distance=8),
    )
    after = before.model_copy(update={"position": before.position.model_copy(update={"y": -29})})
    recovered = strategy.accept_partial_result(state, before, after)
    assert recovered is not None and recovered["goal"] == objective.goal
    delegate = recovered["strategy_state"] if wrapped else recovered
    assert delegate["step_index"] == index
    recovered["budget_remaining"] = account.remaining
    remaining = strategy.propose(recovered, after)
    assert remaining.parameters == step.parameters
    assert remaining.maximum_cost == step.maximum_cost
    assert account.used.max_blocks_changed == 120 and account.remaining.max_blocks_changed == 136
    account = account.reserve("remaining-depth", remaining.maximum_cost).settle(
        "remaining-depth",
        BudgetUsage(max_actions=1, max_blocks_changed=6, max_travel_distance=3),
    )
    recovered = strategy.accept_result(recovered, {})
    reached = after.model_copy(update={"position": after.position.model_copy(update={"y": -32})})
    recovered["budget_remaining"] = account.remaining
    assert strategy.propose(recovered, reached).parameters == {
        "minimum_cobblestone": 0,
        "target_y": -40,
    }
    assert account.limit == limit
    assert account.used.max_blocks_changed == 126 and limit.max_blocks_changed == 256


@pytest.mark.parametrize(
    "after_y", [-24, -23, -24.25, float("nan"), float("inf"), float("-inf"), None]
)
def test_partial_shaft_requires_real_depth_progress_and_a_declared_checkpoint(after_y):
    mission = build_nether_portal_mission(mission_id="partial-shaft-no-progress")
    objective = next(o for o in mission.objectives if o.objective_id == "diamond-pickaxe")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "diamond_pickaxe")
    )
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(objective.goal)
    before = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "position": {"x": -18, "y": -24, "z": 22},
            "inventory": {"iron_pickaxe": 1, "stone_pickaxe": 2, "stick": 4, "cobblestone": 40},
        }
    )
    assert strategy.propose(state, before).capability == "mine_shaft"
    after = before.model_copy(
        update={
            "position": None
            if after_y is None
            else before.position.model_copy(update={"y": after_y})
        }
    )
    assert strategy.accept_partial_result(state, before, after) is None
    advanced = before.model_copy(update={"position": before.position.model_copy(update={"y": -29})})
    state["workflow"] = state["workflow"].model_copy(update={"checkpoints": ()})
    assert strategy.accept_partial_result(state, before, advanced) is None


@pytest.mark.parametrize("target", ["water_bucket", "nether_iron_kit"])
def test_observed_checkpoint_completion_is_recoverable_only_for_the_failed_primitive(target):
    mission = build_nether_portal_mission(mission_id="completed-subgoal-progress")
    objective = next(o for o in mission.objectives if o.goal.target == target)
    registry = WorkflowRegistry()
    registry.register(next(w for w in nether_preparation_workflows() if w.target == target))
    strategy = FallbackStrategy(registry=registry)
    state = strategy.prepare(objective.goal)
    inventory = (
        {"bucket": 1}
        if target == "water_bucket"
        else {
            "stone_pickaxe": 1,
            "raw_iron": 7,
            "furnace": 1,
            "oak_planks": 23,
        }
    )
    before = Observation.model_validate({**MESSAGES["Observation"], "inventory": inventory})
    step = strategy.propose(state, before)
    state["settled_capability"] = step.capability
    if target == "nether_iron_kit":
        # A relative7-item smelt must not be replayed after only3 items arrive.
        incomplete = before.model_copy(
            update={"inventory": {**inventory, "raw_iron": 4, "iron_ingot": 3}}
        )
        assert strategy.accept_partial_result(state, before, incomplete) is None
    after = before.model_copy(
        update={"inventory": {"water_bucket": 1} if target == "water_bucket" else {"iron_ingot": 7}}
    )
    assert GoalVerifier().verify(goal=objective.goal, final=after)["satisfied"]
    assert (
        strategy.accept_partial_result({**state, "settled_capability": "goto"}, before, after)
        is None
    )
    recovered = strategy.accept_partial_result(state, before, after)
    assert recovered is not None and recovered["step_index"] == state["step_index"]
    assert strategy.propose(recovered, after).kind == "complete"


def test_mainline_resume_rejects_stage_missing_from_mission() -> None:
    with pytest.raises(ValueError, match="resume stage 'return-home'"):
        build_nether_portal_mission(mission_id="survival-resume-invalid", resume_from="return-home")


def test_resumed_mission_can_recover_to_a_verified_shore_without_moving_home() -> None:
    mission = build_nether_portal_mission(
        mission_id="recover-pit",
        home=(11, 64, 75),
        resume_from="obsidian",
        recover_at=(58, -54, 123),
    )
    assert [item.objective_id for item in mission.objectives] == [
        "recover-shore",
        "obsidian",
        "return-home",
        "portal",
    ]
    recovery, obsidian, home, _ = mission.objectives
    assert recovery.dependencies == ()
    assert obsidian.dependencies == (recovery.objective_id,)
    assert recovery.goal.success_predicates[0].y == -54
    assert home.goal.success_predicates[0].y == 64
    assert mission.budget.max_travel_distance == 704
    assert mission.budget.max_blocks_changed == 376
    with pytest.raises(ValueError, match="resumed mission"):
        build_nether_portal_mission(mission_id="invalid-recovery", recover_at=(0, 64, 0))


def test_portal_build_places_only_frame_then_ignites_and_retains_interior_evidence() -> None:
    mission = build_nether_portal_mission(mission_id="survival-portal-test")
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"]),
        blueprint_origins={"nether-portal-v1": (0, 64, 0)},
    )
    state = strategy.prepare(mission.objectives[-1].goal)
    observation = Observation.model_validate(MESSAGES["Observation"])
    decisions = []
    for _ in range(16):
        decision = strategy.propose(state, observation)
        decisions.append(decision)
        state = strategy.accept_result(state, {})
    assert [decision.capability for decision in decisions] == ["place"] * 14 + [
        "goto",
        "ignite_portal",
    ]
    materials = [decision.parameters["block_type"] for decision in decisions[:14]]
    assert materials.count("minecraft:obsidian") == 10
    assert materials.count("minecraft:cobbled_deepslate") == 4
    placed = set()
    for decision in decisions[:14]:
        x, y, z = (decision.parameters[key] for key in ("x", "y", "z"))
        assert y == 64 or any(
            neighbour in placed
            for neighbour in ((x - 1, y, z), (x + 1, y, z), (x, y - 1, z), (x, y + 1, z))
        ), "frame placement must not depend on a portal block created later by ignition"
        placed.add((x, y, z))
    complete = strategy.propose(state, observation)
    assert complete.kind == "complete"
    compiled = complete.output["compiled_blueprints"][0]
    assert list(compiled.expected_blocks.values()).count("minecraft:nether_portal") == 6
    assert list(compiled.expected_blocks.values()).count("minecraft:obsidian") == 10
    assert list(compiled.expected_blocks.values()).count("minecraft:cobbled_deepslate") == 4
    assert len(compiled.expected_blocks) == 20


def test_snow_clearance_reservations_fit_the_original_portal_limits() -> None:
    mission = build_nether_portal_mission(mission_id="snow-budget", home=(0, 64.5, 0))
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"]),
        blueprint_origins={"nether-portal-v1": (1, 64, 0)},
    )
    state = strategy.prepare(mission.objectives[-1].goal)
    observation = Observation.model_validate(MESSAGES["Observation"])
    decisions = []
    for _ in range(16):
        decision = strategy.propose(state, observation)
        decisions.append(decision)
        state = strategy.accept_result(state, {})
    placements = decisions[:14]
    assert sum(d.maximum_cost.max_blocks_changed == 2 for d in placements) == 4
    assert all(
        d.maximum_cost.max_blocks_changed == (2 if d.parameters["y"] == 64 else 1)
        for d in placements
    )
    assert sum(d.maximum_cost.max_actions for d in decisions) == 16
    assert sum(d.maximum_cost.max_blocks_changed for d in decisions) == 24
    assert mission.objectives[-1].budget.max_actions == 20
    assert mission.objectives[-1].budget.max_blocks_changed == 24
    assert mission.budget.max_actions == 117
    assert mission.budget.max_blocks_changed == 1088


@pytest.mark.parametrize("position", [(x, y, z) for x in (0, 1) for y in (64, 65) for z in (0, 1)])
def test_snow_home_observation_rounding_uses_the_original_location_tolerance(
    position: tuple[int, int, int],
) -> None:
    mission = build_nether_portal_mission(mission_id="snow-home", home=(0, 64.5, 0))
    goal = next(o.goal for o in mission.objectives if o.objective_id == "water-return")
    final = Observation.model_validate(
        {**MESSAGES["Observation"], "position": dict(zip(("x", "y", "z"), position, strict=True))}
    )
    assert goal.success_predicates[0].tolerance == 1.5
    assert GoalVerifier().verify(goal=goal, final=final)["satisfied"] is True


def test_portal_blueprint_requires_six_real_portal_blocks() -> None:
    from types import SimpleNamespace

    compiled = BlueprintCompiler().compile(
        nether_portal_blueprint(),
        BlueprintBinding(origin=(0, 64, 0), materials={}),
    )
    inspection = SimpleNamespace(
        bounds=compiled.bounds,
        content_hash="a" * 64,
        blocks={
            key: block if block == "minecraft:obsidian" else "minecraft:air"
            for key, block in compiled.expected_blocks.items()
        },
    )
    assert not BlueprintVerifier().verify(compiled, inspection).satisfied
    inspection.blocks = compiled.expected_blocks
    assert BlueprintVerifier().verify(compiled, inspection).satisfied
