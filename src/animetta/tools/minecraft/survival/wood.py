"""Bind survival recipes only after the required carried wood stock is observed."""

from __future__ import annotations

from animetta.tools.gamebot.contracts.v2 import Observation

from .workflows import InventoryThreshold, WorkflowDefinition

_WOOD_TYPES = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry")
_WOOD_LOGS = frozenset(f"{wood}_log" for wood in _WOOD_TYPES)


def inventory_resource_count(
    observation: Observation, item: str, *, combine_species: bool = False
) -> int:
    """Count exact stock; any_log uses one species unless measuring combined growth."""
    resource = item.removeprefix("minecraft:")
    names = _WOOD_LOGS if resource == "any_log" else {resource}
    stocks: dict[str, int] = {}
    for key, count in observation.inventory.items():
        name = key.removeprefix("minecraft:")
        if name in names:
            stocks[name] = max(stocks.get(name, 0), count)
    return sum(stocks.values()) if combine_species else max(stocks.values(), default=0)


def _observed_wood(observation: Observation) -> str | None:
    inventory: dict[str, int] = {}
    for item, count in observation.inventory.items():
        name = item.removeprefix("minecraft:")
        inventory[name] = max(inventory.get(name, 0), count)
    # Recipe choice comes from carried materials rather than a visible tree.
    stock = {
        wood: inventory.get(f"{wood}_log", 0) * 4 + inventory.get(f"{wood}_planks", 0)
        for wood in _WOOD_TYPES
    }
    if max(stock.values()) > 0:
        return max(stock, key=lambda wood: stock[wood])
    return None


def bind_workflow_wood(
    workflow: WorkflowDefinition, observation: Observation
) -> WorkflowDefinition:
    """Keep exact goals and budgets; bind only workflows that allow wood substitution."""
    if not workflow.adaptive_wood:
        return workflow
    wood = _observed_wood(observation)
    log_target = next(
        (
            target
            for target in workflow.collection_targets
            if target is not None and (target.item == "any_log" or target.item in _WOOD_LOGS)
        ),
        None,
    )
    if (
        wood is not None
        and log_target is not None
        and inventory_resource_count(observation, f"{wood}_log") < log_target.quantity
        and not inventory_resource_count(observation, f"{wood}_planks")
    ):
        wood = None
    replacements = (
        {"oak_log": f"{wood}_log", "any_log": f"{wood}_log", "oak_planks": f"{wood}_planks"}
        if wood is not None
        else {"oak_log": "any_log"}
    )

    def threshold(item: InventoryThreshold) -> InventoryThreshold:
        return item.model_copy(update={"item": replacements.get(item.item, item.item)})

    return workflow.model_copy(
        update={
            "adaptive_wood": wood is None,
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
