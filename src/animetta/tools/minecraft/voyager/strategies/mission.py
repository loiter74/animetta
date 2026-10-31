"""Mission-policy strategy selection without a second execution owner."""

from __future__ import annotations

from math import floor, isfinite

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.survival.retreat import propose_retreat

from ..goal_models import GoalSpec
from .base import BoundedStrategy, Complete, ExecuteStep, StrategyDecision, StrategyFailure


class MissionStrategy:
    """Select one authorized bounded strategy from committed observations."""

    def __init__(
        self,
        *,
        builtin: BoundedStrategy | None = None,
        live: BoundedStrategy | None,
        learn: BoundedStrategy | None,
        fallback: BoundedStrategy | None,
        manifest: RuntimeManifest | None = None,
    ) -> None:
        self._can_retreat = manifest is not None and any(
            capability.name == "goto" for capability in manifest.capabilities
        )
        self._strategies = {
            name: strategy
            for name, strategy in (
                ("builtin", builtin),
                ("live", live),
                ("learn", learn),
                ("fallback", fallback),
            )
            if strategy is not None
        }

    def prepare(self, goal: GoalSpec | None) -> dict:
        if goal is None:
            raise ValueError("mission strategy requires a structured goal")
        candidates = tuple(
            name for name in ("builtin", "live", "learn", "fallback") if name in self._strategies
        )
        return {
            "goal": goal,
            "candidates": candidates,
            "candidate_index": 0,
            "selected_strategy": None,
            "strategy_state": None,
            "executed_steps": 0,
            "selection_transitions": (),
        }

    def propose(self, state: dict, observation: Observation) -> StrategyDecision:
        while True:
            selected = state.get("selected_strategy")
            if selected is None:
                candidates = state["candidates"]
                index = state["candidate_index"]
                if index >= len(candidates):
                    return StrategyFailure(
                        code="NO_AUTHORIZED_STRATEGY",
                        message="No mission-policy-authorized strategy can satisfy the goal",
                    )
                selected = candidates[index]
                state["selected_strategy"] = selected
                state["strategy_state"] = self._strategies[selected].prepare(state["goal"])
                state["selection_transitions"] = (
                    *state["selection_transitions"],
                    selected,
                )

            if "budget_remaining" in state:
                state["strategy_state"]["budget_remaining"] = state["budget_remaining"]
            decision = self._strategies[selected].propose(
                state["strategy_state"],
                observation,
            )
            if isinstance(decision, Complete):
                return Complete(output={**decision.output, "selected_strategy": selected})
            if (
                isinstance(decision, ExecuteStep)
                and self._can_retreat
                and state["goal"].intent != "combat"
            ):
                retreat = propose_retreat(state, observation)
                if retreat is not None:
                    return retreat
            if not isinstance(decision, StrategyFailure):
                return decision
            if state["executed_steps"] > 0:
                return decision
            state["candidate_index"] += 1
            state["selected_strategy"] = None
            state["strategy_state"] = None

    def accept_result(self, state: dict, result: object) -> dict:
        target = state.get("pending_retreat")
        if target is not None:
            return {
                **state,
                "pending_retreat": None,
                "retreat_destinations": (*state.get("retreat_destinations", ()), target),
            }
        selected = state["selected_strategy"]
        if not isinstance(selected, str):
            raise ValueError("mission strategy has no selected delegate")
        delegated = self._strategies[selected].accept_result(
            state["strategy_state"],
            result,
        )
        return {
            **state,
            "strategy_state": delegated,
            "executed_steps": state["executed_steps"] + 1,
        }

    def accept_partial_result(
        self,
        state: dict,
        before: Observation,
        after: Observation,
    ) -> dict | None:
        """Forward a settled partial collect only to the selected fallback delegate."""

        if state.get("selected_strategy") != "fallback":
            return None
        fallback = self._strategies.get("fallback")
        accept = getattr(fallback, "accept_partial_result", None)
        if not callable(accept):
            return None
        recovered = accept(state["strategy_state"], before, after)
        if recovered is None:
            return None
        return {
            **state,
            "strategy_state": recovered,
            "executed_steps": state["executed_steps"] + 1,
        }

    def recover_failed_step(
        self,
        state: dict,
        failed_step: ExecuteStep,
        before: Observation,
        after: Observation,
    ) -> dict | None:
        """Re-evaluate the same goal after a known settled failure, without replay."""
        selected = state.get("selected_strategy")
        delegated = state.get("strategy_state")
        if not isinstance(selected, str) or not isinstance(delegated, dict):
            return None
        candidate = {**state, "strategy_state": {**delegated}}
        target = candidate.pop("pending_retreat", None)
        if target is not None:
            candidate["retreat_destinations"] = (
                *candidate.get("retreat_destinations", ()),
                target,
            )
        decision = self.propose(candidate, after)
        if candidate.get("selected_strategy") != selected:
            return None
        if isinstance(decision, Complete):
            return candidate
        same_search = (
            isinstance(decision, ExecuteStep)
            and failed_step.capability == decision.capability == "collect"
            and {k: v for k, v in failed_step.parameters.items() if k != "count"}
            == {k: v for k, v in decision.parameters.items() if k != "count"}
        )
        if (
            isinstance(decision, ExecuteStep)
            and not same_search
            and (
                decision.capability != failed_step.capability
                or decision.parameters != failed_step.parameters
            )
        ):
            return candidate
        if same_search and state.get("settled_error_code") in {
            "RESOURCE_NOT_FOUND",
            "SEARCH_TIMEOUT",
        }:
            previous_origin = self._search_origin(before)
            origin = self._search_origin(after)
            resource = failed_step.parameters.get("block_type")
            visited = state.get("search_origins", ())
            if (
                isinstance(resource, str)
                and previous_origin is not None
                and origin is not None
                and origin != previous_origin
                and (resource, origin) not in visited
                and self._known_cells(after) - self._known_cells(before)
            ):
                candidate["search_origins"] = (
                    *visited,
                    (resource, previous_origin),
                    (resource, origin),
                )
                return candidate
        return None

    @staticmethod
    def _search_origin(observation: Observation) -> tuple[int, int, int] | None:
        p = observation.position
        if p is None or not all(isfinite(v) for v in (p.x, p.y, p.z)):
            return None
        return floor(p.x), floor(p.y), floor(p.z)

    @staticmethod
    def _known_cells(observation: Observation) -> set[tuple[str, int, int, int]]:
        blocks = observation.environment.get("blocks")
        if not isinstance(blocks, dict):
            return set()
        cells: set[tuple[str, int, int, int]] = set()
        for block in blocks.values():
            if not isinstance(block, dict) or not isinstance(block.get("name"), str):
                continue
            position = block.get("position")
            if not isinstance(position, dict):
                continue
            values = tuple(position.get(axis) for axis in ("x", "y", "z"))
            if all(type(v) in (int, float) and isfinite(v) for v in values):
                cells.add((block["name"], floor(values[0]), floor(values[1]), floor(values[2])))
        return cells
