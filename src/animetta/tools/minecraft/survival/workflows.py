"""Typed deterministic workflows adapted from the survival runner phases."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from animetta.tools.minecraft.voyager.budget import BudgetUsage
from animetta.tools.minecraft.voyager.strategies.base import ExecuteStep


class InventoryThreshold(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    item: str = Field(pattern=r"^[a-z0-9_:.-]+$")
    quantity: int = Field(gt=0)


class WorkflowCheckpointClause(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    inventory_all: tuple[InventoryThreshold, ...] = ()
    maximum_y: int | None = None

    @model_validator(mode="after")
    def require_evidence(self) -> WorkflowCheckpointClause:
        if not self.inventory_all and self.maximum_y is None:
            raise ValueError("workflow checkpoint clause requires observable evidence")
        return self


class WorkflowCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    any_of: tuple[WorkflowCheckpointClause, ...] = Field(min_length=1)


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    workflow_id: str
    intent: str
    target: str
    steps: tuple[ExecuteStep, ...]
    checkpoints: tuple[WorkflowCheckpoint | None, ...] = ()
    collection_targets: tuple[InventoryThreshold | None, ...] = ()
    adaptive_wood: bool = False

    @model_validator(mode="after")
    def align_checkpoints(self) -> WorkflowDefinition:
        if self.checkpoints and len(self.checkpoints) != len(self.steps):
            raise ValueError("workflow checkpoints must align with steps")
        return self

    @model_validator(mode="after")
    def align_collection_targets(self) -> WorkflowDefinition:
        if self.collection_targets and len(self.collection_targets) != len(self.steps):
            raise ValueError("workflow collection targets must align with steps")
        return self


def _step(capability: str, parameters: dict, *, travel: float = 0, blocks: int = 0):
    return ExecuteStep(
        capability=capability,
        parameters=parameters,
        maximum_cost=BudgetUsage(
            max_actions=1,
            max_travel_distance=travel,
            max_blocks_changed=blocks,
        ),
    )


def _inventory_checkpoint(*alternatives: dict[str, int]) -> WorkflowCheckpoint:
    return WorkflowCheckpoint(
        any_of=tuple(
            WorkflowCheckpointClause(
                inventory_all=tuple(
                    InventoryThreshold(item=item, quantity=quantity)
                    for item, quantity in requirement.items()
                )
            )
            for requirement in alternatives
        )
    )


def _depth_checkpoint(maximum_y: int, diamond_quantity: int = 1) -> WorkflowCheckpoint:
    return WorkflowCheckpoint(
        any_of=(
            WorkflowCheckpointClause(maximum_y=maximum_y),
            WorkflowCheckpointClause(
                inventory_all=(InventoryThreshold(item="diamond", quantity=diamond_quantity),)
            ),
        )
    )


_BOOTSTRAP_COMPLETE = _inventory_checkpoint(
    {"wooden_pickaxe": 1, "oak_planks": 7, "stick": 2},
    {"stone_pickaxe": 1},
    {"iron_pickaxe": 1},
    {"diamond": 1},
)


def _iron_progression_steps(
    iron_quantity: int = 3, *, ore_batch_size: int | None = None
) -> tuple[ExecuteStep, ...]:
    return (
        _step("collect", {"block_type": "oak_log", "count": 8}, travel=192, blocks=16),
        _step("craft", {"recipe": "oak_planks", "count": 32}),
        _step("craft", {"recipe": "crafting_table", "count": 1}),
        _step("craft", {"recipe": "stick", "count": 4}),
        _step("craft", {"recipe": "wooden_pickaxe", "count": 1}, travel=8, blocks=8),
        # Collection includes the bounded shaft preparation before gathering stone.
        _step("collect", {"block_type": "stone", "count": 16}, travel=96, blocks=96),
        _step("craft", {"recipe": "stone_pickaxe", "count": 1}, travel=8, blocks=8),
        _step(
            "collect",
            {
                "block_type": "iron_ore",
                "count": iron_quantity if ore_batch_size is None else ore_batch_size,
            },
            travel=192,
            blocks=192,
        ),
        # Set up the stationary workstation at the ore site, after travelling.
        _step("craft", {"recipe": "furnace", "count": 1}, travel=8, blocks=8),
        _step(
            "smelt",
            {"item": "raw_iron", "fuel": "oak_planks", "count": iron_quantity},
            travel=8,
            blocks=8,
        ),
    )


def _iron_progression_collection_targets(
    iron_quantity: int = 3,
) -> tuple[InventoryThreshold | None, ...]:
    return (
        InventoryThreshold(item="oak_log", quantity=8),
        None,
        None,
        None,
        None,
        InventoryThreshold(item="cobblestone", quantity=16),
        None,
        InventoryThreshold(item="raw_iron", quantity=iron_quantity),
        None,
        None,
    )


def _iron_progression_checkpoints() -> tuple[WorkflowCheckpoint, ...]:
    return (
        *(_BOOTSTRAP_COMPLETE,) * 5,
        _inventory_checkpoint(
            {"cobblestone": 11},
            {"stone_pickaxe": 1},
            {"iron_pickaxe": 1},
            {"diamond": 1},
        ),
        _inventory_checkpoint({"stone_pickaxe": 1}, {"iron_pickaxe": 1}, {"diamond": 1}),
        _inventory_checkpoint({"raw_iron": 3}, {"iron_ingot": 3}, {"iron_pickaxe": 1}),
        _inventory_checkpoint({"furnace": 1}, {"iron_ingot": 3}, {"iron_pickaxe": 1}),
        _inventory_checkpoint({"iron_ingot": 3}, {"iron_pickaxe": 1}),
    )


def _bounded_diamond_descent() -> tuple[ExecuteStep, ...]:
    return tuple(
        _step(
            "mine_shaft",
            {"target_y": target_y, "minimum_cobblestone": 0},
            travel=24,
            blocks=24,
        )
        for target_y in range(56, -49, -8)
    ) + (
        _step(
            "mine_shaft",
            {"target_y": -54, "minimum_cobblestone": 0},
            travel=24,
            blocks=18,
        ),
    )


def _bounded_diamond_descent_checkpoints(
    diamond_quantity: int = 1,
) -> tuple[WorkflowCheckpoint, ...]:
    return tuple(
        _depth_checkpoint(target_y, diamond_quantity) for target_y in range(56, -49, -8)
    ) + (_depth_checkpoint(-54, diamond_quantity),)


def iron_survival_workflow() -> WorkflowDefinition:
    """The existing wood-to-iron sequence expressed as bounded typed steps."""

    return WorkflowDefinition(
        workflow_id="survival:iron",
        adaptive_wood=True,
        intent="acquire",
        target="iron_ingot",
        steps=_iron_progression_steps(),
        collection_targets=_iron_progression_collection_targets(),
        checkpoints=_iron_progression_checkpoints(),
    )


def diamond_survival_workflow(diamond_quantity: int = 1) -> WorkflowDefinition:
    """Bounded typed actions through the requested diamond stock."""

    descent = _bounded_diamond_descent()
    return WorkflowDefinition(
        workflow_id="survival:diamond",
        adaptive_wood=True,
        intent="acquire",
        target="diamond",
        steps=(
            *_iron_progression_steps(),
            _step("craft", {"recipe": "stick", "count": 4}),
            _step("craft", {"recipe": "iron_pickaxe", "count": 1}),
            *descent,
            _step(
                "collect",
                {"block_type": "diamond_ore", "count": diamond_quantity},
                travel=256 if diamond_quantity > 1 else 128,
                blocks=diamond_quantity,
            ),
        ),
        collection_targets=(
            *_iron_progression_collection_targets(),
            None,
            None,
            *((None,) * len(descent)),
            InventoryThreshold(item="diamond", quantity=diamond_quantity),
        ),
        checkpoints=(
            *_iron_progression_checkpoints(),
            _inventory_checkpoint({"stick": 2}, {"iron_pickaxe": 1}, {"diamond": 1}),
            _inventory_checkpoint({"iron_pickaxe": 1}, {"diamond": 1}),
            *_bounded_diamond_descent_checkpoints(diamond_quantity),
            _inventory_checkpoint({"diamond": diamond_quantity}),
        ),
    )


def nether_preparation_workflows() -> tuple[WorkflowDefinition, ...]:
    """Extend the reviewed survival chain without changing the one-diamond goal."""
    diamond_quantity = 3
    diamond = diamond_survival_workflow(diamond_quantity)
    diamond_stock = _inventory_checkpoint({"diamond": diamond_quantity})
    pickaxe = _inventory_checkpoint({"diamond_pickaxe": 1})
    pickaxe_steps = (
        _step("collect", {"block_type": "stone", "count": 6}, travel=48, blocks=16),
        _step("craft", {"recipe": "stick", "count": 8}),
        _step("craft", {"recipe": "stone_pickaxe", "count": 2}, travel=8, blocks=8),
        *diamond.steps,
        _step("craft", {"recipe": "stick", "count": 4}),
        _step("craft", {"recipe": "diamond_pickaxe", "count": 1}, travel=8, blocks=8),
    )
    pickaxe_collection_targets = (
        InventoryThreshold(item="cobblestone", quantity=6),
        None,
        None,
        *diamond.collection_targets,
        None,
        None,
    )
    checkpoints = (
        *(
            WorkflowCheckpoint(any_of=(*checkpoint.any_of, *diamond_stock.any_of))
            for checkpoint in (
                _inventory_checkpoint({"cobblestone": 6}, {"stone_pickaxe": 2}),
                _inventory_checkpoint({"stick": 4}, {"stone_pickaxe": 2}),
                _inventory_checkpoint({"stone_pickaxe": 2}),
                *diamond.checkpoints,
            )
            if checkpoint is not None
        ),
        _inventory_checkpoint({"stick": 2}),
        pickaxe,
    )
    ignition = _inventory_checkpoint({"flint_and_steel": 1})
    return (
        WorkflowDefinition(
            workflow_id="survival:nether-iron-kit",
            adaptive_wood=True,
            intent="acquire",
            target="nether_iron_kit",
            steps=_iron_progression_steps(7, ore_batch_size=1),
            collection_targets=_iron_progression_collection_targets(7),
            checkpoints=(
                *_iron_progression_checkpoints()[:7],
                _inventory_checkpoint({"raw_iron": 7}, {"iron_ingot": 7}),
                _inventory_checkpoint({"furnace": 1}, {"iron_ingot": 7}),
                _inventory_checkpoint({"iron_ingot": 7}),
            ),
        ),
        WorkflowDefinition(
            workflow_id="survival:iron-pickaxe",
            intent="craft",
            target="iron_pickaxe",
            steps=(
                _step("craft", {"recipe": "stick", "count": 4}),
                _step("craft", {"recipe": "iron_pickaxe", "count": 1}),
            ),
            checkpoints=(
                _inventory_checkpoint({"stick": 2}, {"iron_pickaxe": 1}),
                _inventory_checkpoint({"iron_pickaxe": 1}),
            ),
        ),
        WorkflowDefinition(
            workflow_id="survival:water-bucket",
            intent="acquire",
            target="water_bucket",
            steps=(
                _step("craft", {"recipe": "bucket", "count": 1}, travel=8, blocks=8),
                _step("fill_water_bucket", {}, travel=120, blocks=1),
            ),
            checkpoints=(
                _inventory_checkpoint({"bucket": 1}, {"water_bucket": 1}),
                _inventory_checkpoint({"water_bucket": 1}),
            ),
        ),
        WorkflowDefinition(
            workflow_id="survival:diamond-pickaxe",
            adaptive_wood=True,
            intent="craft",
            target="diamond_pickaxe",
            steps=pickaxe_steps,
            collection_targets=pickaxe_collection_targets,
            checkpoints=tuple(
                WorkflowCheckpoint(any_of=(*checkpoint.any_of, *pickaxe.any_of))
                for checkpoint in checkpoints
                if checkpoint is not None
            ),
        ),
        WorkflowDefinition(
            workflow_id="survival:ignition",
            adaptive_wood=True,
            intent="craft",
            target="flint_and_steel",
            steps=(
                _step("collect", {"block_type": "oak_log", "count": 2}, travel=64, blocks=2),
                _step("craft", {"recipe": "oak_planks", "count": 8}),
                _step("collect", {"block_type": "iron_ore", "count": 1}, travel=64, blocks=1),
                _step(
                    "smelt",
                    {"item": "raw_iron", "fuel": "oak_planks", "count": 1},
                    travel=8,
                    blocks=8,
                ),
                _step("acquire_flint", {"max_attempts": 16}, travel=64, blocks=48),
                _step("craft", {"recipe": "flint_and_steel", "count": 1}),
            ),
            collection_targets=(
                InventoryThreshold(item="oak_log", quantity=2),
                None,
                InventoryThreshold(item="raw_iron", quantity=1),
                None,
                None,
                None,
            ),
            checkpoints=tuple(
                WorkflowCheckpoint(any_of=(*checkpoint.any_of, *ignition.any_of))
                for checkpoint in (
                    _inventory_checkpoint({"oak_planks": 3}, {"iron_ingot": 1}),
                    _inventory_checkpoint({"oak_planks": 3}, {"iron_ingot": 1}),
                    _inventory_checkpoint({"raw_iron": 1}, {"iron_ingot": 1}),
                    _inventory_checkpoint({"iron_ingot": 1}),
                    _inventory_checkpoint({"flint": 1}),
                    ignition,
                )
            ),
        ),
        WorkflowDefinition(
            workflow_id="survival:obsidian",
            intent="acquire",
            target="obsidian",
            steps=(_step("prepare_obsidian", {}, travel=128, blocks=16),)
            + tuple(
                # Four bounded dig attempts, each followed by a verified backfill.
                _step("collect", {"block_type": "obsidian", "count": 1}, travel=64, blocks=8)
                for _ in range(10)
            ),
            collection_targets=(None,)
            + tuple(InventoryThreshold(item="obsidian", quantity=count) for count in range(1, 11)),
            checkpoints=(None,)
            + tuple(_inventory_checkpoint({"obsidian": count}) for count in range(1, 11)),
        ),
    )
