"""Mission-policy strategy selection without a second execution owner."""

from __future__ import annotations

from math import dist, floor, isfinite

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.survival.recovery import propose_recovery_move
from animetta.tools.minecraft.survival.retreat import propose_retreat

from ..budget import ExecutionBudget, budget_usage_from_vector
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
        self._recovery_move_minimum = (
            budget_usage_from_vector(manifest.capability("explore_surface").maximum_cost)
            if manifest is not None
            and any(c.name == "explore_surface" for c in manifest.capabilities)
            else None
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
        if "skill_candidate" in goal.constraints:
            candidates = ("learn",) if "learn" in self._strategies else ()
        elif goal.constraints.get("learning_mode") == "model_generated_only":
            candidates = tuple(name for name in candidates if name != "learn")
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
        decision = self._propose(state, observation)
        if isinstance(decision, ExecuteStep) and decision.capability == "goto":
            goal = state.get("goal")
            timeout = goal.constraints.get("navigation_timeout_ms") if goal is not None else None
            if timeout is not None:
                decision = decision.model_copy(
                    update={"parameters": {**decision.parameters, "navigation_timeout_ms": timeout}}
                )
        return decision

    def _propose(self, state: dict, observation: Observation) -> StrategyDecision:
        pending_move = state.get("pending_recovery_move")
        if isinstance(pending_move, ExecuteStep):
            return pending_move
        previous_position = state.pop("recovery_probe_origin", None)
        if previous_position is not None:
            position = observation.position
            if position is None:
                return StrategyFailure(
                    code="RECOVERY_STATE_UNKNOWN", message="Recovery position missing"
                )
            if dist(previous_position, (position.x, position.y, position.z)) < 1:
                recovered = self._schedule_recovery_move(state, observation)
                if recovered is None:
                    return StrategyFailure(
                        code="RECOVERY_NO_EXECUTABLE_ALTERNATIVE",
                        message="No untried recovery column fits the remaining original budget",
                    )
                state.update(recovered)
                return state["pending_recovery_move"]
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
                output = {**decision.output, "selected_strategy": selected}
                if state.get("recovery_decisions"):
                    output["recovery_decisions"] = state["recovery_decisions"]
                return Complete(output=output)
            if (
                isinstance(decision, ExecuteStep)
                and self._can_retreat
                and selected != "live"
                and not state["strategy_state"].get("generated_program")
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
        if state.get("pending_recovery_move") is not None:
            return {**state, "pending_recovery_move": None}
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
        """Forward settled subgoal progress only to the selected fallback delegate."""

        pending = state.get("pending_recovery_move")
        if (
            isinstance(pending, ExecuteStep)
            and state.get("settled_capability") == pending.capability
            and before.world_identity == after.world_identity
            and before.environment.get("dimension") == after.environment.get("dimension")
        ):
            # A settled auxiliary budget stop is not workflow progress. The next
            # proposal sees the freshly charged account and checks actual movement.
            return {**state, "pending_recovery_move": None}

        if state.get("selected_strategy") != "fallback":
            return None
        fallback = self._strategies.get("fallback")
        accept = getattr(fallback, "accept_partial_result", None)
        if not callable(accept):
            return None
        delegated = state["strategy_state"]
        if "settled_capability" in state:
            delegated = {**delegated, "settled_capability": state["settled_capability"]}
        recovered = accept(delegated, before, after)
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
        if state.get("pending_recovery_move") is not None:
            if state.get("settled_error_code") not in {
                "SEARCH_TIMEOUT",
                "NAVIGATION_TARGET_NOT_REACHED",
                "RESOURCE_NOT_FOUND",
                "UNSAFE_AREA",
            } or (
                before.world_identity != after.world_identity
                or before.environment.get("dimension") != after.environment.get("dimension")
            ):
                return None
            if self._recovery_progress(before, after):
                return {**state, "pending_recovery_move": None}
            return self._schedule_recovery_move(state, after)
        if selected == "live" or delegated.get("generated_program"):
            # IR frames advance when proposing. Generic re-proposal would silently
            # skip the failed action; only an explicit program handler may recover.
            recover = getattr(self._strategies[selected], "recover_failed_step", None)
            if not callable(recover):
                return None
            recovered = recover(
                {
                    **delegated,
                    **{
                        key: state[key]
                        for key in ("settled_error_code", "settled_feedback")
                        if key in state
                    },
                },
                failed_step,
                before,
                after,
            )
            if recovered is None:
                return None
            return {
                **state,
                "strategy_state": recovered,
                "executed_steps": state["executed_steps"] + 1,
            }
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
        if (
            isinstance(decision, ExecuteStep)
            and failed_step.capability == decision.capability == "goto"
            and failed_step.parameters == decision.parameters
            and state.get("settled_error_code")
            in {"SEARCH_TIMEOUT", "NAVIGATION_TARGET_NOT_REACHED"}
            and before.world_identity == after.world_identity
            and before.position is not None
            and after.position is not None
        ):
            remaining = state.get("budget_remaining")
            target = tuple(decision.parameters.get(axis) for axis in ("x", "y", "z"))
            start = (before.position.x, before.position.y, before.position.z)
            end = (after.position.x, after.position.y, after.position.z)
            if (
                isinstance(remaining, ExecutionBudget)
                and remaining.max_actions >= decision.maximum_cost.max_actions
                and remaining.max_strategy_attempts >= decision.maximum_cost.max_strategy_attempts
                and remaining.max_travel_distance > 0
                and all(type(v) in (int, float) and isfinite(v) for v in (*target, *start, *end))
                and dist(start, target) - dist(end, target) >= 1
            ):
                candidate["executed_steps"] = state["executed_steps"] + 1
                return candidate
        if same_search and state.get("settled_error_code") in {
            "RESOURCE_NOT_FOUND",
            "SEARCH_TIMEOUT",
        }:
            previous_origin = self._search_origin(before)
            origin = self._search_origin(after)
            resource = failed_step.parameters.get("block_type")
            visited = state.get("search_origins", ())
            before_cells, after_cells = self._known_cells(before), self._known_cells(after)
            old_names = {(x, y, z): name for name, x, y, z in before_cells}
            dimension = after.environment.get("dimension")
            changed_subjects: set[str] = set()
            if (
                isinstance(dimension, str)
                and dimension
                and before.environment.get("dimension") == dimension
            ):
                dimension = dimension if ":" in dimension else f"minecraft:{dimension}"
                changed_subjects = {
                    f"block:{dimension}:{x}:{y}:{z}"
                    for name, x, y, z in after_cells
                    if old_names.get((x, y, z), name) != name
                }
            moved = (
                origin != previous_origin
                and (resource, origin) not in visited
                and bool(after_cells - before_cells)
            )
            changed_in_place = origin == previous_origin and bool(
                changed_subjects.intersection(state.get("settled_block_subjects", ()))
            )
            scenes = state.get("search_scenes", ())
            scene = (resource, origin, tuple(sorted(after_cells)))
            if (
                isinstance(resource, str)
                and previous_origin is not None
                and origin is not None
                and (moved or changed_in_place)
                and scene not in scenes
            ):
                candidate["search_origins"] = (
                    *visited,
                    (resource, previous_origin),
                    (resource, origin),
                )
                candidate["search_scenes"] = (
                    *scenes,
                    (resource, previous_origin, tuple(sorted(before_cells))),
                    scene,
                )
                return candidate
        if (
            selected == "fallback"
            and self._recovery_move_minimum is not None
            and failed_step.capability in {"collect", "mine_shaft"}
            and state.get("settled_error_code")
            in {
                "RESOURCE_NOT_FOUND",
                "SEARCH_TIMEOUT",
                "MINE_SHAFT_STUCK",
                "NAVIGATION_TARGET_NOT_REACHED",
            }
            and before.world_identity == after.world_identity
            and before.environment.get("dimension") == after.environment.get("dimension")
            and isinstance(state.get("budget_remaining"), ExecutionBudget)
        ):
            return self._schedule_recovery_move(state, after)
        return None

    def _schedule_recovery_move(self, state: dict, observation: Observation) -> dict | None:
        remaining = state.get("budget_remaining")
        origin = self._search_origin(observation)
        position = observation.position
        if (
            self._recovery_move_minimum is None
            or origin is None
            or position is None
            or not isinstance(remaining, ExecutionBudget)
        ):
            return None
        anchor = state.get("recovery_anchor", origin)
        attempted = state.get("recovery_targets", ())
        move = propose_recovery_move(
            observation,
            remaining=remaining,
            minimum_cost=self._recovery_move_minimum,
            anchor=anchor,
            attempted=attempted,
        )
        if move is None:
            return None
        target = (move.parameters["x"], move.parameters["z"])
        feedback = state.get("settled_feedback", {})
        return {
            **state,
            "pending_recovery_move": move,
            "recovery_anchor": anchor,
            "recovery_probe_origin": (
                position.x,
                position.y,
                position.z,
            ),
            "recovery_targets": (*attempted, target),
            "recovery_decisions": (
                *state.get("recovery_decisions", ()),
                {
                    "error_code": state.get("settled_error_code"),
                    "receipt_hash": feedback.get("receipt_hash"),
                    "target": target,
                },
            ),
        }

    @staticmethod
    def _recovery_progress(before: Observation, after: Observation) -> bool:
        return (
            before.world_identity == after.world_identity
            and before.environment.get("dimension") == after.environment.get("dimension")
            and before.position is not None
            and after.position is not None
            and dist(
                (before.position.x, before.position.y, before.position.z),
                (after.position.x, after.position.y, after.position.z),
            )
            >= 1
        )

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
