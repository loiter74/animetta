"""Closed, typed mission primitives owned by the Voyager control plane."""

from __future__ import annotations

from collections.abc import Mapping
from math import floor, hypot

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.blueprint import (
    BlueprintBinding,
    BlueprintCompiler,
    CompiledBlueprint,
    starter_shelter_blueprint,
)
from animetta.tools.minecraft.blueprint.portal import nether_portal_blueprint
from animetta.tools.minecraft.survival.food import propose_food_recovery

from ..budget import BudgetUsage, ExecutionBudget
from ..goal_models import (
    EntityDefeated,
    FoodAtLeast,
    GoalSpec,
    HealthAtLeast,
    LocationReached,
    StructureMatchesBlueprint,
)
from .base import Complete, ExecuteStep, StrategyDecision, StrategyFailure


class BuiltinMissionStrategy:
    """Execute only reviewed combat and blueprint primitives.

    The public boundary remains a typed goal: callers cannot provide these
    concrete action steps or select this strategy themselves.
    """

    def __init__(
        self,
        *,
        manifest: RuntimeManifest,
        blueprint_origins: Mapping[str, tuple[int, int, int]] | None = None,
        entity_origins: Mapping[str, tuple[int, int, int]] | None = None,
        execution_budget: ExecutionBudget | None = None,
    ) -> None:
        self._manifest = manifest
        self._blueprint_origins = dict(blueprint_origins or {})
        self._entity_origins = dict(entity_origins or {})
        self._execution_budget = execution_budget
        shelter = starter_shelter_blueprint()
        self._blueprints = {shelter.blueprint_id: shelter}
        portal = nether_portal_blueprint()
        self._blueprints[portal.blueprint_id] = portal

    def prepare(self, goal: GoalSpec | None) -> dict:
        if goal is None:
            raise ValueError("builtin mission strategy requires a structured goal")
        if goal.intent == "survive" and goal.target == "food-recovery":
            health = next(
                (
                    predicate
                    for predicate in goal.success_predicates
                    if isinstance(predicate, HealthAtLeast)
                ),
                None,
            )
            if health is not None:
                return {
                    "goal": goal,
                    "kind": "food-recovery",
                    "predicate": health,
                    "food_predicates": tuple(
                        predicate
                        for predicate in goal.success_predicates
                        if isinstance(predicate, FoodAtLeast)
                    ),
                    "completed_steps": 0,
                }
        combat = next(
            (
                predicate
                for predicate in goal.success_predicates
                if isinstance(predicate, EntityDefeated)
            ),
            None,
        )
        structure = next(
            (
                predicate
                for predicate in goal.success_predicates
                if isinstance(predicate, StructureMatchesBlueprint)
            ),
            None,
        )
        location = next(
            (
                predicate
                for predicate in goal.success_predicates
                if isinstance(predicate, LocationReached)
            ),
            None,
        )
        if goal.intent == "combat" and combat is not None:
            return {
                "goal": goal,
                "kind": "combat",
                "predicate": combat,
                "completed_steps": 0,
                "zone_attempted": False,
                "pending_kind": None,
            }
        if goal.intent == "build" and structure is not None:
            blueprint = self._blueprints.get(structure.blueprint_id)
            if blueprint is None or blueprint.canonical_hash != structure.blueprint_hash:
                return {"goal": goal, "failure_code": "BLUEPRINT_NOT_APPROVED"}
            return {
                "goal": goal,
                "kind": "blueprint",
                "blueprint": blueprint,
                "compiled_blueprint": None,
                "completed_steps": 0,
            }
        if goal.intent == "travel" and location is not None:
            return {
                "goal": goal,
                "kind": "travel",
                "predicate": location,
                "completed_steps": 0,
            }
        return {"goal": goal, "failure_code": "UNSUPPORTED_BUILTIN_GOAL"}

    def propose(self, state: dict, observation: Observation) -> StrategyDecision:
        failure = state.get("failure_code")
        if failure is not None:
            return StrategyFailure(
                code=str(failure),
                message="Goal is not handled by the closed builtin catalog",
            )
        if state["kind"] == "food-recovery":
            return propose_food_recovery(state, observation)
        if state["kind"] == "combat":
            return self._propose_combat(state, observation)
        if state["kind"] == "travel":
            return self._propose_travel(state)
        return self._propose_blueprint(state, observation)

    def _propose_travel(self, state: dict) -> StrategyDecision:
        predicate: LocationReached = state["predicate"]
        budget = self._execution_budget
        if state["completed_steps"] >= 1:
            return Complete(output={"builtin_kind": "travel"})
        try:
            self._manifest.capability("goto")
        except KeyError:
            return StrategyFailure(
                code="CAPABILITY_NOT_AUTHORIZED",
                message="Runtime does not expose the typed goto capability",
            )
        return ExecuteStep(
            capability="goto",
            parameters={"x": predicate.x, "y": predicate.y, "z": predicate.z},
            maximum_cost=BudgetUsage(
                max_actions=1,
                max_strategy_attempts=1,
                max_travel_distance=budget.max_travel_distance if budget else 64,
                max_blocks_changed=budget.max_blocks_changed if budget else 0,
                max_damage_taken=budget.max_damage_taken if budget else 0,
                resource_consumption=budget.resource_consumption if budget else {},
            ),
        )

    def _propose_combat(self, state: dict, observation: Observation) -> StrategyDecision:
        predicate: EntityDefeated = state["predicate"]
        if state["completed_steps"] >= predicate.quantity:
            return Complete(output={"builtin_kind": "combat"})
        try:
            capability = self._manifest.capability("attack")
        except KeyError:
            return StrategyFailure(
                code="CAPABILITY_NOT_AUTHORIZED",
                message="Runtime does not expose the typed attack capability",
            )
        matching = tuple(
            entity
            for entity in observation.visible_entities
            if entity.entity_type == predicate.entity
        )
        if not matching:
            origin = self._entity_origins.get(predicate.entity)
            if origin is not None and not state["zone_attempted"]:
                try:
                    self._manifest.capability("goto")
                except KeyError:
                    return StrategyFailure(
                        code="CAPABILITY_NOT_AUTHORIZED",
                        message="Runtime does not expose typed travel to the combat zone",
                    )
                target = origin
                if observation.position is not None:
                    dx = origin[0] - observation.position.x
                    dz = origin[2] - observation.position.z
                    distance = hypot(dx, dz)
                    if distance > 3:
                        scale = (distance - 3) / distance
                        target = (
                            round(observation.position.x + dx * scale),
                            origin[1],
                            round(observation.position.z + dz * scale),
                        )
                state["pending_kind"] = "combat_travel"
                return ExecuteStep(
                    capability="goto",
                    parameters={"x": target[0], "y": target[1], "z": target[2]},
                    maximum_cost=BudgetUsage(
                        max_actions=1,
                        max_strategy_attempts=1,
                        max_travel_distance=32,
                    ),
                )
            return StrategyFailure(
                code="COMBAT_TARGET_NOT_OBSERVED",
                message=f"No committed observation contains {predicate.entity}",
            )
        properties = capability.parameters_schema.get("properties", {})
        if isinstance(properties, dict) and "target_entity_id" in properties:
            parameters: dict[str, object] = {
                "target_entity_id": matching[0].entity_id,
            }
        else:
            parameters = {"target": predicate.entity.removeprefix("minecraft:")}
        state["pending_kind"] = "combat_attack"
        return ExecuteStep(
            capability="attack",
            parameters=parameters,
            maximum_cost=BudgetUsage(
                max_actions=1,
                max_strategy_attempts=1,
                max_travel_distance=32,
                max_damage_taken=2,
            ),
        )

    def _propose_blueprint(self, state: dict, observation: Observation) -> StrategyDecision:
        compiled: CompiledBlueprint | None = state["compiled_blueprint"]
        if compiled is None:
            blueprint = state["blueprint"]
            origin = self._blueprint_origins.get(blueprint.blueprint_id)
            if origin is None:
                if observation.position is None:
                    return StrategyFailure(
                        code="BUILD_ORIGIN_UNAVAILABLE",
                        message="A committed position is required to bind the blueprint",
                    )
                origin = (
                    floor(observation.position.x),
                    floor(observation.position.y),
                    floor(observation.position.z),
                )
            compiled = BlueprintCompiler().compile(
                blueprint,
                BlueprintBinding(origin=origin, materials={}),
            )
            if blueprint.blueprint_id == "nether-portal-v1":
                compiled = compiled.model_copy(
                    update={
                        "steps": tuple(
                            step
                            for step in compiled.steps
                            if step.block_id != "minecraft:nether_portal"
                        ),
                    }
                )
            state["compiled_blueprint"] = compiled
        index = state["completed_steps"]
        if compiled.blueprint_id == "nether-portal-v1" and index == len(compiled.steps):
            x, y, z = compiled.origin
            return ExecuteStep(
                capability="goto",
                parameters={"x": x + 1, "y": y, "z": z + 2},
                maximum_cost=BudgetUsage(max_actions=1, max_travel_distance=8),
            )
        if compiled.blueprint_id == "nether-portal-v1" and index == len(compiled.steps) + 1:
            x, y, z = compiled.origin
            return ExecuteStep(
                capability="ignite_portal",
                parameters={"x": x, "y": y, "z": z},
                maximum_cost=BudgetUsage(
                    max_actions=1,
                    max_travel_distance=8,
                    max_blocks_changed=6,
                ),
            )
        if index >= len(compiled.steps):
            return Complete(
                output={
                    "builtin_kind": "blueprint",
                    "compiled_blueprints": (compiled,),
                }
            )
        placement = compiled.steps[index]
        return ExecuteStep(
            capability="place",
            parameters=placement.parameters,
            maximum_cost=BudgetUsage(
                max_actions=1,
                max_blocks_changed=len(placement.effect_positions),
                max_travel_distance=8 if compiled.blueprint_id == "nether-portal-v1" else 0,
            ),
        )

    def accept_result(self, state: dict, result: object) -> dict:
        del result
        if state.get("pending_kind") == "combat_travel":
            return {**state, "zone_attempted": True, "pending_kind": None}
        return {
            **state,
            "completed_steps": state["completed_steps"] + 1,
            "pending_kind": None,
        }
