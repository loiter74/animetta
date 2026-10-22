"""Explicit deterministic workflow strategy with no implicit goal substitution."""

from __future__ import annotations

from animetta.tools.gamebot.contracts.v2 import Observation
from animetta.tools.minecraft.survival.registry import WorkflowRegistry
from animetta.tools.minecraft.survival.workflows import (
    InventoryThreshold,
    WorkflowCheckpoint,
    WorkflowDefinition,
)

from ..goal_models import GoalSpec
from .base import Complete, StrategyDecision, StrategyFailure


class FallbackStrategy:
    def __init__(self, *, registry: WorkflowRegistry) -> None:
        self._registry = registry

    def prepare(self, goal: GoalSpec | None) -> dict:
        if goal is None:
            raise ValueError("fallback requires a structured goal")
        workflow = self._registry.resolve(goal)
        if workflow is None:
            return {
                "goal": goal,
                "goal_hash": goal.canonical_hash,
                "failure_code": "UNSUPPORTED_FALLBACK_GOAL",
                "learning_evidence_eligible": False,
            }
        return {
            "goal": goal,
            "goal_hash": goal.canonical_hash,
            "workflow": workflow,
            "step_index": 0,
            "learning_evidence_eligible": False,
        }

    def propose(self, state: dict, observation: Observation) -> StrategyDecision:
        if state.get("failure_code"):
            return StrategyFailure(
                code=state["failure_code"], message="No exact deterministic workflow"
            )
        workflow = state["workflow"]
        index = state["step_index"]
        while index < len(workflow.steps):
            checkpoint = workflow.checkpoints[index] if workflow.checkpoints else None
            if checkpoint is not None and self._checkpoint_satisfied(checkpoint, observation):
                index += 1
                state["step_index"] = index
                continue
            step = workflow.steps[index]
            target = self._declared_collection_target(workflow, index)
            if target is None or step.capability != "collect":
                break
            remaining = target.quantity - self._inventory_count(observation, target.item)
            if remaining <= 0:
                index += 1
                state["step_index"] = index
                continue
            count = step.parameters.get("count")
            if isinstance(count, int) and count > remaining:
                return step.model_copy(
                    update={"parameters": {**step.parameters, "count": remaining}}
                )
            return step
        if index >= len(workflow.steps):
            return Complete(
                output={
                    "workflow_id": workflow.workflow_id,
                    "learning_evidence_eligible": False,
                }
            )
        return workflow.steps[index]

    def accept_partial_result(
        self,
        state: dict,
        before: Observation,
        after: Observation,
    ) -> dict | None:
        """Accept a settled partial collect when the declared target made progress."""

        workflow = state.get("workflow")
        index = state.get("step_index")
        if workflow is None or index is None or index >= len(workflow.steps):
            return None
        step = workflow.steps[index]
        target = self._declared_collection_target(workflow, index)
        if target is None or step.capability != "collect":
            return None
        if self._inventory_count(after, target.item) <= self._inventory_count(before, target.item):
            return None
        return {**state}

    @staticmethod
    def _declared_collection_target(
        workflow: WorkflowDefinition,
        index: int,
    ) -> InventoryThreshold | None:
        if not workflow.collection_targets:
            return None
        return workflow.collection_targets[index]

    @staticmethod
    def _inventory_count(observation: Observation, item: str) -> int:
        resource = item.removeprefix("minecraft:")
        return max(
            (
                count
                for key, count in observation.inventory.items()
                if key.removeprefix("minecraft:") == resource
            ),
            default=0,
        )

    @staticmethod
    def _checkpoint_satisfied(checkpoint: WorkflowCheckpoint, observation: Observation) -> bool:
        for clause in checkpoint.any_of:
            inventory_satisfied = all(
                FallbackStrategy._inventory_count(observation, threshold.item) >= threshold.quantity
                for threshold in clause.inventory_all
            )
            depth_satisfied = clause.maximum_y is None or (
                observation.position is not None and observation.position.y <= clause.maximum_y
            )
            if inventory_satisfied and depth_satisfied:
                return True
        return False

    def accept_result(self, state: dict, result: object) -> dict:
        del result
        return {**state, "step_index": state["step_index"] + 1}
