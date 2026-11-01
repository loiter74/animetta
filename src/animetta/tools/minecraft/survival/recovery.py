"""Bounded recovery exploration through the existing native terrain validator."""

from __future__ import annotations

from math import dist, isfinite
from typing import TYPE_CHECKING

from animetta.tools.gamebot.contracts.v2 import Observation
from animetta.tools.minecraft.voyager.budget import BudgetUsage, ExecutionBudget

if TYPE_CHECKING:
    from animetta.tools.minecraft.voyager.strategies.base import ExecuteStep


def propose_recovery_move(
    observation: Observation,
    *,
    remaining: ExecutionBudget,
    minimum_cost: BudgetUsage,
    anchor: tuple[int, int, int],
    attempted: tuple[tuple[int, int], ...],
) -> ExecuteStep | None:
    """Search eight columns once, without inventing missing voxel observations.

    Native explore_surface validates dry paths and cannot dig. Its receipt and
    the next fresh observation determine progress; a success label alone does not.
    """
    from animetta.tools.minecraft.voyager.strategies.base import ExecuteStep

    position = observation.position
    travel_limit = min(16.0, remaining.max_travel_distance - 2)
    if (
        position is None
        or not all(isfinite(v) for v in (position.x, position.y, position.z))
        or remaining.max_actions < max(1, minimum_cost.max_actions) + 1
        or remaining.max_strategy_attempts < minimum_cost.max_strategy_attempts
        or minimum_cost.max_blocks_changed
        or minimum_cost.max_damage_taken
        or minimum_cost.resource_consumption
        or travel_limit < minimum_cost.max_travel_distance
    ):
        return None
    for dx, dz in ((8, 0), (8, 8), (0, 8), (-8, 8), (-8, 0), (-8, -8), (0, -8), (8, -8)):
        x, z = anchor[0] + dx, anchor[2] + dz
        distance = dist((position.x, position.z), (x, z))
        if (x, z) in attempted or not 3 <= distance <= travel_limit - 2:
            continue
        return ExecuteStep(
            capability="explore_surface",
            parameters={"x": x, "z": z},
            maximum_cost=minimum_cost.model_copy(
                update={
                    "max_actions": max(1, minimum_cost.max_actions),
                    "max_travel_distance": travel_limit,
                }
            ),
        )
    return None
