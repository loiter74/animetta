"""Bind a substitutable survival wood chain once from observed inventory or logs."""

from __future__ import annotations

from animetta.tools.gamebot.contracts.v2 import Observation

from .workflows import InventoryThreshold, WorkflowDefinition

_WOOD_TYPES = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry")


def _observed_wood(observation: Observation) -> str:
    inventory: dict[str, int] = {}
    for item, count in observation.inventory.items():
        name = item.removeprefix("minecraft:")
        inventory[name] = max(inventory.get(name, 0), count)
    # Reuse carried stock before switching to another tree during recovery.
    stock = {
        wood: inventory.get(f"{wood}_log", 0) * 4 + inventory.get(f"{wood}_planks", 0)
        for wood in _WOOD_TYPES
    }
    if max(stock.values()) > 0:
        return max(stock, key=lambda wood: stock[wood])
    position = observation.position
    candidates = [
        block
        for block in observation.visible_blocks
        if block.block_id.removeprefix("minecraft:") in {f"{wood}_log" for wood in _WOOD_TYPES}
    ]
    if candidates and position is not None:
        nearest = min(
            candidates,
            key=lambda block: sum(
                (getattr(block.position, axis) - getattr(position, axis)) ** 2
                for axis in ("x", "y", "z")
            ),
        )
        return nearest.block_id.removeprefix("minecraft:").removesuffix("_log")
    return "oak"


def bind_workflow_wood(
    workflow: WorkflowDefinition, observation: Observation
) -> WorkflowDefinition:
    """Keep exact goals and budgets; bind only workflows that allow wood substitution."""
    if not workflow.adaptive_wood:
        return workflow
    wood = _observed_wood(observation)
    replacements = {"oak_log": f"{wood}_log", "oak_planks": f"{wood}_planks"}

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
