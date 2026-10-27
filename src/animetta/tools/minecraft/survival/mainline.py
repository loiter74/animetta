"""Finite survival mission from an empty inventory to an activated portal."""

from typing import Literal

from animetta.tools.minecraft.blueprint.portal import nether_portal_blueprint
from animetta.tools.minecraft.mission.models import ExecutionPolicy, MissionObjective, MissionSpec
from animetta.tools.minecraft.voyager.budget import BudgetUsage, ExecutionBudget
from animetta.tools.minecraft.voyager.goal_models import (
    AcquireGoal,
    BuildGoal,
    CraftGoal,
    InventoryAtLeast,
    LocationReached,
    StructureMatchesBlueprint,
    TravelGoal,
)


def build_nether_portal_mission(
    *,
    mission_id: str,
    home: tuple[float, float, float] | None = None,
    resume_from: Literal[
        "iron",
        "iron-pickaxe",
        "water-return",
        "water-bucket",
        "ignition",
        "diamond-pickaxe",
        "obsidian",
        "return-home",
        "portal",
    ] = "iron",
    recover_at: tuple[float, float, float] | None = None,
) -> MissionSpec:
    """Keep planning in Anima; use only reviewed workflows and runtime actions.

    ``resume_from`` keeps only the objective suffix starting at that stage: the
    first retained objective drops its dependency and later ones still depend on
    their immediate predecessor. The mission budget is recomputed from retained
    objectives only. Callers must pick the stage from verified prefix facts;
    this builder never fabricates completion for skipped stages.
    A verified ``recover_at`` shore may precede a resumed suffix without moving
    the original home or portal site.
    """
    blueprint = nether_portal_blueprint()
    objectives: list[MissionObjective] = []
    for objective_id, intent, target, quantity, actions, travel, blocks in (
        ("iron", "acquire", "nether_iron_kit", 7, 16, 512, 256),
        ("iron-pickaxe", "craft", "iron_pickaxe", 1, 3, 0, 0),
        ("water-bucket", "acquire", "water_bucket", 1, 4, 128, 8),
        ("ignition", "craft", "flint_and_steel", 1, 8, 128, 64),
        ("diamond-pickaxe", "craft", "diamond_pickaxe", 1, 40, 384, 256),
        # Preparation (16) plus ten collections (at most 8 changes each).
        ("obsidian", "acquire", "obsidian", 10, 16, 256, 96),
    ):
        if objective_id == "water-bucket" and home is not None:
            objectives.append(
                MissionObjective(
                    objective_id="water-return",
                    dependencies=(objectives[-1].objective_id,),
                    goal=TravelGoal(
                        intent="travel",
                        target="surface-water-access",
                        success_predicates=(
                            LocationReached(
                                kind="location_reached", x=home[0], y=home[1], z=home[2]
                            ),
                        ),
                    ),
                    budget=BudgetUsage(
                        max_actions=2,
                        max_strategy_attempts=1,
                        max_travel_distance=192,
                        max_blocks_changed=128,
                    ),
                )
            )
        item = "iron_ingot" if target == "nether_iron_kit" else target
        predicates = (InventoryAtLeast(kind="inventory_at_least", item=item, quantity=quantity),)
        goal = (
            CraftGoal(
                intent="craft", target=target, quantity=quantity, success_predicates=predicates
            )
            if intent == "craft"
            else AcquireGoal(
                intent="acquire", target=target, quantity=quantity, success_predicates=predicates
            )
        )
        objectives.append(
            MissionObjective(
                objective_id=objective_id,
                dependencies=(objectives[-1].objective_id,) if objectives else (),
                goal=goal,
                budget=BudgetUsage(
                    max_actions=actions,
                    max_strategy_attempts=1,
                    max_travel_distance=travel,
                    max_blocks_changed=blocks,
                    max_damage_taken={"diamond-pickaxe": 2, "iron-pickaxe": 0}.get(objective_id, 1),
                ),
            )
        )
    if home is not None:
        objectives.append(
            MissionObjective(
                objective_id="return-home",
                dependencies=(objectives[-1].objective_id,),
                goal=TravelGoal(
                    intent="travel",
                    target="portal-site",
                    success_predicates=(
                        LocationReached(kind="location_reached", x=home[0], y=home[1], z=home[2]),
                    ),
                ),
                budget=BudgetUsage(
                    max_actions=8,
                    max_strategy_attempts=1,
                    max_travel_distance=256,
                    max_blocks_changed=256,
                    max_damage_taken=1,
                ),
            )
        )
    objectives.append(
        MissionObjective(
            objective_id="portal",
            dependencies=(objectives[-1].objective_id,),
            goal=BuildGoal(
                intent="build",
                target="nether_portal",
                success_predicates=(
                    StructureMatchesBlueprint(
                        kind="structure_matches_blueprint",
                        blueprint_id=blueprint.blueprint_id,
                        blueprint_hash=blueprint.canonical_hash,
                    ),
                ),
            ),
            budget=BudgetUsage(
                max_actions=20,
                max_strategy_attempts=1,
                max_travel_distance=128,
                max_blocks_changed=24,
                max_damage_taken=1,
                resource_consumption={"minecraft:obsidian": 10, "minecraft:cobbled_deepslate": 4},
            ),
        )
    )
    objective_ids = [objective.objective_id for objective in objectives]
    if resume_from not in objective_ids:
        raise ValueError(f"resume stage {resume_from!r} is not part of this mission")
    start = objective_ids.index(resume_from)
    retained = objectives[start:]
    retained[0] = retained[0].model_copy(update={"dependencies": ()})
    if recover_at is not None:
        if resume_from == "iron":
            raise ValueError("shore recovery requires a resumed mission stage")
        retained[0] = retained[0].model_copy(update={"dependencies": ("recover-shore",)})
        retained.insert(
            0,
            MissionObjective(
                objective_id="recover-shore",
                goal=TravelGoal(
                    intent="travel",
                    target="safe-shore",
                    success_predicates=(
                        LocationReached(
                            kind="location_reached",
                            x=recover_at[0],
                            y=recover_at[1],
                            z=recover_at[2],
                        ),
                    ),
                ),
                budget=BudgetUsage(max_actions=2, max_strategy_attempts=1, max_travel_distance=64),
            ),
        )
    usage = BudgetUsage()
    for objective in retained:
        usage = usage.plus(objective.budget)
    return MissionSpec(
        mission_id=mission_id,
        objectives=tuple(retained),
        budget=ExecutionBudget(
            queue_timeout_ms=60_000,
            execution_timeout_ms=3_600_000,
            **usage.model_dump(),
        ),
        execution=ExecutionPolicy(reuse_trusted_skill=True, allow_deterministic_fallback=True),
    )
