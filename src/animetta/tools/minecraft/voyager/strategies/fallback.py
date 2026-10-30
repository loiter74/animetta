"""Explicit deterministic workflow strategy with no implicit goal substitution."""

from __future__ import annotations

from animetta.tools.gamebot.contracts.v2 import Observation
from animetta.tools.minecraft.survival.registry import WorkflowRegistry
from animetta.tools.minecraft.survival.wood import bind_workflow_wood, inventory_resource_count
from animetta.tools.minecraft.survival.workflows import (
    InventoryThreshold,
    WorkflowCheckpoint,
    WorkflowDefinition,
)

from ..budget import BudgetUsage, ExecutionBudget
from ..goal_models import GoalSpec
from .base import Complete, ExecuteStep, StrategyDecision, StrategyFailure


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
        workflow = bind_workflow_wood(state["workflow"], observation)
        state["workflow"] = workflow
        state.pop("repeat_collection", None)
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
            if isinstance(count, int) and count < remaining:
                state["repeat_collection"] = True
            if isinstance(count, int) and count > remaining:
                step = step.model_copy(
                    update={"parameters": {**step.parameters, "count": remaining}}
                )
            return self._bounded_collection_step(
                state, workflow, index, target, remaining, step, observation
            )
        if index >= len(workflow.steps):
            return Complete(
                output={
                    "workflow_id": workflow.workflow_id,
                    "learning_evidence_eligible": False,
                }
            )
        return workflow.steps[index]

    def _bounded_collection_step(
        self,
        state: dict,
        workflow: WorkflowDefinition,
        index: int,
        target: InventoryThreshold,
        remaining: int,
        step: ExecuteStep,
        observation: Observation,
    ) -> ExecuteStep | StrategyFailure:
        """Tighten repeated batches using the controller's current account snapshot."""
        available = state.get("budget_remaining")
        batch_size = workflow.steps[index].parameters.get("count")
        if (
            not isinstance(available, ExecutionBudget)
            or not isinstance(batch_size, int)
            or batch_size <= 0
            or batch_size >= target.quantity
        ):
            return step
        count = step.parameters["count"]
        pending = remaining - count
        followup = BudgetUsage(
            max_actions=(pending + batch_size - 1) // batch_size,
            max_blocks_changed=pending,
        )
        for future_index in range(index + 1, len(workflow.steps)):
            checkpoint = workflow.checkpoints[future_index] if workflow.checkpoints else None
            if checkpoint is not None and self._checkpoint_satisfied(checkpoint, observation):
                continue
            followup = followup.plus(workflow.steps[future_index].maximum_cost)
        maximum = step.maximum_cost
        blocks = min(
            maximum.max_blocks_changed, available.max_blocks_changed - followup.max_blocks_changed
        )
        travel = min(
            maximum.max_travel_distance,
            available.max_travel_distance - followup.max_travel_distance,
        )
        # Keep the runtime's existing two-block stopping reserve in this batch.
        if (
            blocks < count + 2
            or travel < 0
            or available.max_actions < maximum.max_actions + followup.max_actions
        ):
            return StrategyFailure(
                code="BUDGET_EXHAUSTED",
                message="Remaining budget cannot cover the collection batch and remaining workflow",
            )
        return step.model_copy(
            update={
                "maximum_cost": maximum.model_copy(
                    update={"max_blocks_changed": blocks, "max_travel_distance": travel}
                )
            }
        )

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
        return inventory_resource_count(observation, item)

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
        updated = {**state}
        # Successful batches share the original command account and absolute target.
        if not updated.pop("repeat_collection", False):
            updated["step_index"] += 1
        return updated
