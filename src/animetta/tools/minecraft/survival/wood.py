"""Use material families without confusing them with a single-species recipe."""

from __future__ import annotations

from animetta.tools.gamebot.contracts.v2 import Observation

from .workflows import InventoryThreshold, WorkflowDefinition

_WOOD_TYPES = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry")
_WOOD_LOGS = frozenset(f"{wood}_log" for wood in _WOOD_TYPES)
_WOOD_PLANKS = frozenset(f"{wood}_planks" for wood in _WOOD_TYPES)


def inventory_resource_count(observation: Observation, item: str) -> int:
    """Aggregate family stock while aliases of the same real item remain nonadditive."""
    resource = item.removeprefix("minecraft:")
    names = (
        _WOOD_LOGS
        if resource == "any_log"
        else _WOOD_PLANKS
        if resource == "any_planks"
        else {resource}
    )
    stocks: dict[str, int] = {}
    for key, count in observation.inventory.items():
        name = key.removeprefix("minecraft:")
        if name in names:
            stocks[name] = max(stocks.get(name, 0), count)
    return sum(stocks.values())


def bind_workflow_wood(workflow: WorkflowDefinition) -> WorkflowDefinition:
    """Bind opted-in workflows to native families, preserving all goals and budgets."""
    if not workflow.adaptive_wood:
        return workflow
    replacements = {"oak_log": "any_log", "oak_planks": "any_planks"}

    def threshold(item: InventoryThreshold) -> InventoryThreshold:
        return item.model_copy(update={"item": replacements.get(item.item, item.item)})

    return workflow.model_copy(
        update={
            "adaptive_wood": False,
            "steps": tuple(
                step.model_copy(
                    update={
                        "parameters": {
                            key: replacements.get(value, value) if isinstance(value, str) else value
                            for key, value in step.parameters.items()
                        }
                    }
                )
                for step in workflow.steps
            ),
            "collection_targets": tuple(
                threshold(item) if item else None for item in workflow.collection_targets
            ),
            "shared_collection_budget_items": tuple(
                replacements.get(item, item) for item in workflow.shared_collection_budget_items
            ),
            "checkpoints": tuple(
                checkpoint.model_copy(
                    update={
                        "any_of": tuple(
                            clause.model_copy(
                                update={
                                    "inventory_all": tuple(
                                        threshold(item) for item in clause.inventory_all
                                    )
                                }
                            )
                            for clause in checkpoint.any_of
                        )
                    }
                )
                if checkpoint
                else None
                for checkpoint in workflow.checkpoints
            ),
        }
    )
