"""Explicit deterministic workflow strategy with no implicit goal substitution."""

from __future__ import annotations

from math import ceil, isfinite

from animetta.tools.gamebot.contracts.v2 import Observation
from animetta.tools.minecraft.survival.registry import WorkflowRegistry
from animetta.tools.minecraft.survival.wood import bind_workflow_wood, inventory_resource_count
from animetta.tools.minecraft.survival.workflows import (
    InventoryThreshold,
    WorkflowCheckpoint,
    WorkflowDefinition,
)

from ..budget import BudgetAccount, BudgetExceededError, BudgetUsage, ExecutionBudget
from ..goal_models import GoalSpec
from .base import Complete, ExecuteStep, StrategyDecision, StrategyFailure

# Below this height the bot is in the mining band (iron ore, mine shafts):
# trees sit on the surface far outside the bounded collect search's digging
# reach, while coal ore — eight smelts per unit — lives in the same band.
_FUEL_COAL_MAX_Y = 56.0


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
        workflow = bind_workflow_wood(state["workflow"])
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
            # A native success is not proof that an absolute inventory target
            # was met, especially when any_log yields a different species.
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
        step = workflow.steps[index]
        if step.capability == "smelt":
            fuel_step = self._plank_fuel_provision_step(step, observation)
            if fuel_step is not None:
                # Provisioning settles without advancing the plan: the same
                # smelt step is re-proposed once the fuel gap is closed. The
                # coal-sufficient smelt override is the smelt itself, so it
                # settles and advances normally.
                if fuel_step.capability != "smelt":
                    state["repeat_collection"] = True
                return fuel_step
        available = state.get("budget_remaining")
        if step.capability == "acquire_flint" and isinstance(available, ExecutionBudget):
            # A failed gravel search can leave reusable gravel and an unspent
            # command allowance. Preserve the final craft while reserving only
            # the work that remains, rather than requesting the original 48 again.
            try:
                work = BudgetAccount(limit=available).reserve(
                    "workflow-followup", self._future_cost(workflow, index, observation)
                )
                maximum = step.maximum_cost.bounded_work(work.remaining)
                minimum_blocks = 2 if self._inventory_count(observation, "gravel") else 1
                if maximum.max_blocks_changed < minimum_blocks:
                    raise BudgetExceededError("BUDGET_EXHAUSTED")
                work.reserve("flint-continuation", maximum)
            except BudgetExceededError:
                return StrategyFailure(
                    code="BUDGET_EXHAUSTED",
                    message="Remaining command budget cannot cover flint work and follow-up craft",
                )
            return step.model_copy(update={"maximum_cost": maximum})
        if step.capability == "mine_shaft" and isinstance(available, ExecutionBudget):
            return step.model_copy(
                update={"maximum_cost": step.maximum_cost.bounded_work(available)}
            )
        return step

    def _plank_fuel_provision_step(
        self, step: ExecuteStep, observation: Observation
    ) -> ExecuteStep | None:
        """Synthesize fuel provisioning when a mixed-plank smelt lacks fuel.

        The furnace burns one plank per 1.5 smelted items; a resumed mission
        often reaches the smelt with the wood steps already checkpoint-skipped
        and too few planks in stock. Above the mining band, collect the
        missing logs first, then craft them into planks. Underground — the
        bot typically sits in the iron-ore band after mining, with the
        surface far outside the bounded search's digging reach — coal ore
        sits in the same band and one coal smelts eight items, so the
        strategy provisions coal and switches the smelt onto it instead.
        """

        fuel = step.parameters.get("fuel")
        count = step.parameters.get("count")
        if fuel != "any_planks" or not isinstance(count, int) or count <= 0:
            return None
        position = observation.position
        if position is not None and position.y <= _FUEL_COAL_MAX_Y:
            return self._coal_fuel_provision_step(step, count, observation)
        required = max(1, ceil(count * 2 / 3))
        planks = inventory_resource_count(observation, "any_planks")
        missing = required - planks
        if missing <= 0:
            return None
        logs = inventory_resource_count(observation, "any_log")
        craftable = 4 * logs
        if craftable >= missing:
            return ExecuteStep(
                capability="craft",
                parameters={"recipe": "any_planks", "count": missing},
                maximum_cost=BudgetUsage(max_actions=1),
            )
        logs_needed = ceil((missing - craftable) / 4)
        return ExecuteStep(
            capability="collect",
            parameters={"block_type": "any_log", "count": logs_needed},
            maximum_cost=BudgetUsage(
                max_actions=1,
                max_travel_distance=192,
                # One dig per log plus the runtime's two-block stopping reserve.
                max_blocks_changed=2 * logs_needed + 2,
                max_damage_taken=1.0,
            ),
        )

    def _coal_fuel_provision_step(
        self, step: ExecuteStep, count: int, observation: Observation
    ) -> ExecuteStep:
        """Underground fuel fallback: coal ore is in reach when trees are not."""
        required = max(1, ceil(count / 8))
        coal = self._inventory_count(observation, "coal")
        if coal >= required:
            return step.model_copy(update={"parameters": {**step.parameters, "fuel": "coal"}})
        return ExecuteStep(
            capability="collect",
            parameters={"block_type": "coal_ore", "count": required - coal},
            maximum_cost=BudgetUsage(
                max_actions=1,
                max_travel_distance=192,
                # One dig per ore plus the runtime's two-block stopping reserve.
                max_blocks_changed=2 * (required - coal) + 2,
                max_damage_taken=1.0,
            ),
        )

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
        """Allocate declared collection work from the current command account."""
        available = state.get("budget_remaining")
        batch_size = workflow.steps[index].parameters.get("count")
        shared_blocks = target.item in workflow.shared_collection_budget_items
        if (
            not isinstance(available, ExecutionBudget)
            or not isinstance(batch_size, int)
            or batch_size <= 0
            or (batch_size >= target.quantity and not shared_blocks)
        ):
            return step
        future = self._future_cost(workflow, index, observation)
        maximum = step.maximum_cost
        count = step.parameters["count"]
        if maximum.max_actions == 1:
            later_batches = available.max_actions - future.max_actions - 1
            if later_batches >= 0:
                # Pack already-authorized material work into this action instead
                # of borrowing another action after a settled recovery.
                count = max(count, remaining - later_batches * batch_size)
        if count != step.parameters["count"]:
            step = step.model_copy(update={"parameters": {**step.parameters, "count": count}})
        pending = remaining - count
        followup = future.plus(
            BudgetUsage(
                max_actions=(pending + batch_size - 1) // batch_size,
                max_blocks_changed=pending,
            )
        )
        blocks = available.max_blocks_changed - followup.max_blocks_changed
        if not shared_blocks:
            blocks = min(maximum.max_blocks_changed, blocks)
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
        """Keep a declared material or depth frontier when observed progress is partial."""

        workflow = state.get("workflow")
        index = state.get("step_index")
        if workflow is None or index is None or index >= len(workflow.steps):
            return None
        step = workflow.steps[index]
        if state.get("settled_capability", step.capability) != step.capability:
            return None
        checkpoint = workflow.checkpoints[index] if workflow.checkpoints else None
        if (
            checkpoint is not None
            and not self._checkpoint_satisfied(checkpoint, before)
            and self._checkpoint_satisfied(checkpoint, after)
        ):
            return {**state}
        if step.capability == "acquire_flint" and checkpoint is not None:
            # Gravel is a reusable input to the native flint loop, not completion
            # of the flint checkpoint. Keep this exact workflow step selected.
            return (
                {**state}
                if self._inventory_count(after, "gravel") > self._inventory_count(before, "gravel")
                else None
            )
        if step.capability == "mine_shaft":
            target_y = step.parameters.get("target_y")
            if (
                type(target_y) is int
                and checkpoint is not None
                and any(clause.maximum_y == target_y for clause in checkpoint.any_of)
                and before.position is not None
                and after.position is not None
                and isfinite(before.position.y)
                and isfinite(after.position.y)
                and before.position.y > target_y
                and after.position.y <= before.position.y - 1
            ):
                return {**state}
            return None
        target = self._declared_collection_target(workflow, index)
        if target is None or step.capability != "collect":
            return None
        if inventory_resource_count(after, target.item) <= inventory_resource_count(
            before, target.item
        ):
            return None
        return {**state}

    def _future_cost(
        self, workflow: WorkflowDefinition, index: int, observation: Observation
    ) -> BudgetUsage:
        future = BudgetUsage()
        for future_index in range(index + 1, len(workflow.steps)):
            checkpoint = workflow.checkpoints[future_index] if workflow.checkpoints else None
            if checkpoint is None or not self._checkpoint_satisfied(checkpoint, observation):
                future = future.plus(workflow.steps[future_index].maximum_cost)
        return future

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
                observation.position is not None
                and isfinite(observation.position.y)
                and observation.position.y <= clause.maximum_y
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
