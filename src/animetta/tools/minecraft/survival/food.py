"""Finite food recovery selected from committed observations, without runtime I/O."""

from __future__ import annotations

from math import floor
from typing import TYPE_CHECKING

from animetta.tools.gamebot.contracts.v2 import Observation
from animetta.tools.minecraft.mission.models import MissionObjective, MissionSpec
from animetta.tools.minecraft.voyager.budget import BudgetUsage, ExecutionBudget
from animetta.tools.minecraft.voyager.goal_models import FoodAtLeast, HealthAtLeast, SurviveGoal

if TYPE_CHECKING:
    from animetta.tools.minecraft.voyager.strategies.base import StrategyDecision

SAFE_FOODS = (
    "cooked_beef",
    "cooked_porkchop",
    "cooked_mutton",
    "cooked_chicken",
    "cooked_rabbit",
    "cooked_salmon",
    "cooked_cod",
    "bread",
    "baked_potato",
    "apple",
    "carrot",
    "beef",
    "porkchop",
    "mutton",
    "rabbit",
    "salmon",
    "cod",
    "melon_slice",
    "sweet_berries",
    "glow_berries",
    "beetroot",
    "potato",
)


def build_food_recovery_mission(
    *, mission_id: str, health: float = 8, food: int | None = None
) -> MissionSpec:
    usage = BudgetUsage(
        max_actions=96,
        max_strategy_attempts=4,
        max_travel_distance=256,
        max_blocks_changed=768,
        max_damage_taken=1,
    )
    success_predicates: tuple[HealthAtLeast | FoodAtLeast, ...] = (
        HealthAtLeast(kind="health_at_least", health=health),
    )
    if food is not None:
        success_predicates += (FoodAtLeast(kind="food_at_least", food=food),)
    return MissionSpec(
        mission_id=mission_id,
        objectives=(
            MissionObjective(
                objective_id="recover-health",
                goal=SurviveGoal(
                    intent="survive",
                    target="food-recovery",
                    success_predicates=success_predicates,
                ),
                budget=usage,
            ),
        ),
        budget=ExecutionBudget(
            queue_timeout_ms=60_000, execution_timeout_ms=900_000, **usage.model_dump()
        ),
    )


def propose_food_recovery(state: dict, observation: Observation) -> StrategyDecision:
    """Eat, regenerate, hunt observed passive animals, or forage observed oak leaves."""
    from animetta.tools.minecraft.voyager.strategies.base import (
        Complete,
        ExecuteStep,
        StrategyFailure,
    )

    health_satisfied = (
        observation.health is not None and observation.health >= state["predicate"].health
    )
    food_predicates = tuple(state.get("food_predicates") or ())
    food_satisfied = all(
        observation.food is not None and observation.food >= predicate.food
        for predicate in food_predicates
    )
    if health_satisfied and food_satisfied:
        return Complete(output={"builtin_kind": "food-recovery"})
    if state["completed_steps"] >= 96:
        return StrategyFailure(
            code="RECOVERY_BUDGET_EXHAUSTED", message="Finite recovery exhausted"
        )
    if observation.food is None or observation.position is None:
        return StrategyFailure(code="RECOVERY_STATE_UNKNOWN", message="Food and position required")

    def step(
        capability: str, parameters: dict, *, travel: float = 0, blocks: int = 0
    ) -> ExecuteStep:
        return ExecuteStep(
            capability=capability,
            parameters=parameters,
            maximum_cost=BudgetUsage(
                max_actions=1,
                max_travel_distance=travel,
                max_blocks_changed=blocks,
                max_damage_taken=1,
            ),
        )

    if food_satisfied and observation.food >= 18:
        return step("wait_for_regeneration", {})
    for item in SAFE_FOODS:
        if observation.inventory.get(item, observation.inventory.get(f"minecraft:{item}", 0)) > 0:
            return step("eat", {"item": item})
    for entity in observation.visible_entities:
        name = entity.entity_type.removeprefix("minecraft:")
        if name in {"cow", "pig", "sheep"}:
            return step("attack", {"target": name}, travel=32)
    leaves = tuple(
        (block.position.x, block.position.y, block.position.z)
        for block in observation.visible_blocks
        if block.block_id in {"minecraft:oak_leaves", "minecraft:dark_oak_leaves"}
    )
    state["forage_stalls"] = (
        state.get("forage_stalls", 0) + 1 if leaves == state.get("previous_leaves") else 0
    )
    state["previous_leaves"] = leaves
    if leaves and state["forage_stalls"] < 2:
        return step("forage_apples", {"max_blocks": 8}, travel=16, blocks=8)
    origin = state.setdefault("search_origin", observation.position)
    waypoints = ((16, 0), (16, 16), (0, 16), (-16, 16), (-16, 0), (-16, -16), (0, -16), (16, -16))
    index = state.get("search_index", 0)
    if index >= len(waypoints):
        return StrategyFailure(code="FOOD_NOT_OBSERVED", message="No food in bounded search")
    dx, dz = waypoints[index]
    state["search_index"] = index + 1
    return step(
        "explore_surface",
        {"x": floor(origin.x) + dx, "z": floor(origin.z) + dz},
        travel=64,
    )
