"""Choose a native-verified retreat from the current committed observation."""

from __future__ import annotations

from math import dist, isfinite
from typing import TYPE_CHECKING

from animetta.tools.gamebot.contracts.v2 import Observation
from animetta.tools.minecraft.voyager.budget import BudgetUsage, ExecutionBudget

if TYPE_CHECKING:
    from animetta.tools.minecraft.voyager.strategies.base import ExecuteStep


def propose_retreat(state: dict, observation: Observation) -> ExecuteStep | None:
    from animetta.tools.minecraft.voyager.strategies.base import ExecuteStep

    available = state.get("budget_remaining")
    position = observation.position
    evidence = observation.environment.get("survival_retreat")
    if (
        not isinstance(available, ExecutionBudget)
        or available.max_actions < 1
        or position is None
        or not isinstance(evidence, dict)
    ):
        return None
    observed_origin = evidence.get("origin")
    if not isinstance(observed_origin, dict):
        return None
    origin = tuple(observed_origin.get(axis) for axis in ("x", "y", "z"))
    if not all(type(value) in (int, float) and isfinite(value) for value in origin):
        return None
    visited = state.get("retreat_destinations", ())
    candidates = []
    destinations = evidence.get("candidates")
    if not isinstance(destinations, list):
        return None
    for candidate in destinations:
        if not isinstance(candidate, dict):
            continue
        target = tuple(candidate.get(axis) for axis in ("x", "y", "z"))
        if not all(
            type(value) in (int, float) and isfinite(value) and value == int(value)
            for value in target
        ):
            continue
        travel = dist(origin, (target[0] + 0.5, target[1], target[2] + 0.5))
        if target not in visited and travel > 0 and travel + 2 < available.max_travel_distance:
            candidates.append((travel, target))
    if not candidates:
        return None
    _, target = min(candidates)
    state["pending_retreat"] = target
    return ExecuteStep(
        capability="goto",
        parameters=dict(zip(("x", "y", "z"), target, strict=True)),
        maximum_cost=BudgetUsage(max_actions=1, max_travel_distance=available.max_travel_distance),
    )
