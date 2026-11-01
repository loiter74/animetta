"""Pure bounded Skill IR interpretation, independent of revision trust selection."""

from __future__ import annotations

from typing import Any

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.skill.ir import (
    ActionStep,
    BranchStep,
    FailStep,
    GoalInputExpression,
    LiteralExpression,
    ObservationExpression,
    Predicate,
    RepeatStep,
    SkillRevision,
    StepOutputExpression,
)

from ..budget import BudgetUsage
from ..goal_models import GoalSpec
from .base import Complete, ExecuteStep, StrategyDecision, StrategyFailure


class SkillProgramStrategy:
    def __init__(
        self,
        *,
        manifest: RuntimeManifest,
        revision: SkillRevision | None = None,
        bindings: dict[str, object] | None = None,
    ) -> None:
        self._manifest = manifest
        self._program_revision = revision
        self._program_bindings = dict(bindings or {})

    @staticmethod
    def _bound_defaults(
        revision: SkillRevision | None, bindings: dict[str, object]
    ) -> dict[str, object]:
        defaults = (
            {p.name: p.default for p in revision.program.parameters if p.default is not None}
            if revision
            else {}
        )
        return {**defaults, **bindings}

    def prepare(self, goal: GoalSpec | None) -> dict:
        if goal is None:
            raise ValueError("live strategy requires a structured goal")
        revision = self._program_revision
        return {
            "goal": goal,
            "revision": revision,
            "frames": ({"kind": "sequence", "steps": revision.program.steps, "index": 0},)
            if revision
            else (),
            "bound_parameters": self._bound_defaults(revision, self._program_bindings),
            "selection_exclusions": (),
            "selection_pending": False,
            "outputs": {},
            "current_action": None,
            "pending_postconditions": (),
            "preconditions_checked": False,
        }

    @staticmethod
    def _path(value: object, path: str) -> object:
        if path.startswith("inventory."):
            inventory = (
                value.get("inventory", {})
                if isinstance(value, dict)
                else getattr(value, "inventory", {})
            )
            item = path.removeprefix("inventory.")
            aliases = {item}
            if ":" not in item or item.startswith("minecraft:"):
                bare = item.removeprefix("minecraft:")
                aliases = {bare, f"minecraft:{bare}"}
            return max(
                (inventory[k] for k in aliases if k in inventory and type(inventory[k]) is int),
                default=0,
            )
        current = value
        for segment in filter(None, path.split(".")):
            if isinstance(current, dict):
                current = current.get(segment)
            elif hasattr(current, segment):
                current = getattr(current, segment)
            else:
                return None
        return current

    def _expression(
        self,
        expression: object,
        *,
        goal: GoalSpec,
        observation: Observation,
        outputs: dict[str, object],
        bindings: dict[str, object],
    ) -> Any:
        if isinstance(expression, LiteralExpression):
            return expression.value
        if isinstance(expression, GoalInputExpression):
            if expression.name in bindings:
                return bindings[expression.name]
            return {
                "target": goal.target,
                "quantity": goal.quantity,
                "count": goal.quantity,
            }.get(expression.name)
        if isinstance(expression, ObservationExpression):
            return self._path(observation, expression.path)
        if isinstance(expression, StepOutputExpression):
            return self._path(outputs.get(expression.step_id), expression.path)
        raise ValueError("unsupported Skill IR expression")

    def _predicate(
        self,
        predicate: Predicate,
        *,
        goal: GoalSpec,
        observation: Observation,
        outputs: dict[str, object],
        bindings: dict[str, object],
    ) -> bool:
        left = self._expression(
            predicate.left,
            goal=goal,
            observation=observation,
            outputs=outputs,
            bindings=bindings,
        )
        right = self._expression(
            predicate.right,
            goal=goal,
            observation=observation,
            outputs=outputs,
            bindings=bindings,
        )
        operations = {
            "eq": lambda: left == right,
            "ne": lambda: left != right,
            "lt": lambda: left < right,
            "lte": lambda: left <= right,
            "gt": lambda: left > right,
            "gte": lambda: left >= right,
            "contains": lambda: right in left,
        }
        try:
            return bool(operations[predicate.op]())
        except (KeyError, TypeError):
            return False

    def _resolve_parameters(
        self,
        step: ActionStep,
        *,
        goal: GoalSpec,
        observation: Observation,
        outputs: dict[str, object],
        bindings: dict[str, object],
    ) -> dict:
        return {
            name: self._expression(
                expression,
                goal=goal,
                observation=observation,
                outputs=outputs,
                bindings=bindings,
            )
            for name, expression in step.parameters.items()
        }

    def propose(self, state: dict, observation: Observation) -> StrategyDecision:
        revision = state["revision"]
        if revision is None:
            return StrategyFailure(
                code="NO_ELIGIBLE_SKILL",
                message="No trusted revision matches the current environment",
            )
        frames = [dict(frame) for frame in state["frames"]]
        goal = state["goal"]
        outputs = state["outputs"]
        bindings = state["bound_parameters"]
        if not state.get("preconditions_checked"):
            if not all(
                self._predicate(
                    predicate,
                    goal=goal,
                    observation=observation,
                    outputs=outputs,
                    bindings=bindings,
                )
                for predicate in revision.program.preconditions
            ):
                return StrategyFailure(
                    code="SKILL_PRECONDITION_FAILED",
                    message="Skill revision preconditions were not satisfied",
                )
            state["preconditions_checked"] = True
        pending = state.get("pending_postconditions", ())
        if pending and not all(
            self._predicate(
                predicate,
                goal=goal,
                observation=observation,
                outputs=outputs,
                bindings=bindings,
            )
            for predicate in pending
        ):
            return StrategyFailure(
                code="ACTION_POSTCONDITION_FAILED",
                message="Skill action postconditions were not satisfied",
            )
        state["pending_postconditions"] = ()
        while frames:
            frame = frames[-1]
            if frame["kind"] == "repeat":
                repeat = frame["step"]
                if frame["iteration"] >= repeat.max_iterations or (
                    repeat.condition is not None
                    and not self._predicate(
                        repeat.condition,
                        goal=goal,
                        observation=observation,
                        outputs=outputs,
                        bindings=bindings,
                    )
                ):
                    frames.pop()
                    continue
                frame["iteration"] += 1
                frames.append({"kind": "sequence", "steps": repeat.steps, "index": 0})
                continue

            if frame["index"] >= len(frame["steps"]):
                frames.pop()
                continue
            step = frame["steps"][frame["index"]]
            frame["index"] += 1
            if isinstance(step, FailStep):
                state["frames"] = tuple(frames)
                return StrategyFailure(code=step.code, message=step.message)
            if isinstance(step, BranchStep):
                branch = (
                    step.then_steps
                    if self._predicate(
                        step.condition,
                        goal=goal,
                        observation=observation,
                        outputs=outputs,
                        bindings=bindings,
                    )
                    else step.else_steps
                )
                frames.append({"kind": "sequence", "steps": branch, "index": 0})
                continue
            if isinstance(step, RepeatStep):
                frames.append({"kind": "repeat", "step": step, "iteration": 0})
                continue
            if isinstance(step, ActionStep):
                capability = self._manifest.capability(step.capability)
                maximum = (
                    step.maximum_cost if step.maximum_cost is not None else capability.maximum_cost
                )
                state["frames"] = tuple(frames)
                state["current_action"] = step.step_id
                state["recover_on_error"] = step.recover_on_error
                state["pending_postconditions"] = step.postconditions
                return ExecuteStep(
                    capability=step.capability,
                    parameters=self._resolve_parameters(
                        step,
                        goal=goal,
                        observation=observation,
                        outputs=outputs,
                        bindings=bindings,
                    ),
                    maximum_cost=BudgetUsage(
                        max_actions=maximum.max_actions,
                        max_strategy_attempts=maximum.max_strategy_attempts,
                        max_travel_distance=maximum.max_travel_distance,
                        max_blocks_changed=maximum.max_blocks_changed,
                        max_damage_taken=maximum.max_damage_taken,
                        resource_consumption=maximum.resource_consumption,
                    ),
                )

        if not all(
            self._predicate(
                predicate,
                goal=goal,
                observation=observation,
                outputs=outputs,
                bindings=bindings,
            )
            for predicate in revision.program.postconditions
        ):
            return StrategyFailure(
                code="SKILL_POSTCONDITION_FAILED",
                message="Skill revision postconditions were not satisfied",
            )
        state["frames"] = ()
        return Complete(output={"revision_hash": revision.revision_hash})

    def accept_result(self, state: dict, result: object) -> dict:
        outputs = dict(state["outputs"])
        current_action = state.get("current_action")
        if current_action is not None:
            outputs[current_action] = result
        return {**state, "outputs": outputs, "current_action": None}

    def recover_failed_step(
        self, state: dict, failed_step: ExecuteStep, before: Observation, after: Observation
    ) -> dict | None:
        del failed_step
        feedback = state.get("settled_feedback")
        if (
            not state.get("recover_on_error")
            or state["recover_on_error"] != state.get("settled_error_code")
            or before.world_identity != after.world_identity
            or not isinstance(feedback, dict)
            or not feedback.get("receipt_hash")
            or feedback.get("outcome") != "error"
        ):
            return None
        recovered = self.accept_result(state, feedback)
        return {**recovered, "pending_postconditions": (), "recover_on_error": None}
