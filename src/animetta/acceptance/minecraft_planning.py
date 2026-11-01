"""Pure pre-submission checks for model-generated bounded Minecraft plans."""

from __future__ import annotations

import json
from collections.abc import Mapping
from math import dist

from pydantic import BaseModel, ConfigDict

from animetta.tools.minecraft.mission.models import MissionSpec
from animetta.tools.minecraft.survival.workflows import (
    InventoryThreshold,
    WorkflowCheckpoint,
    WorkflowCheckpointClause,
)
from animetta.tools.minecraft.voyager.goal_models import GoalSpec, InventoryAtLeast, LocationReached
from animetta.tools.minecraft.voyager.goal_verifier import _resource_id

NETHER_DESCENT_ACCESS_RULE = (
    "钻石镐工作流缺少钻石时会下降矿井，可能失去当前岸边可达性。"
    "若计划还需取水，应在下降前备水，或用已授权的同岸边位置目标在下降后返回再取水；"
    "已有足量钻石、成品镐或水桶时不强制该顺序。"
)


class PlanningIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    objective_id: str | None = None
    required_any_of: tuple[WorkflowCheckpointClause, ...] = ()
    candidate_dependencies: tuple[str, ...] = ()


def nether_plan_inventory_requirements() -> dict[tuple[str, str], WorkflowCheckpoint]:
    """Known necessary inputs of reviewed workflows, not a complete recipe catalog."""

    def alternatives(*items: dict[str, int]) -> WorkflowCheckpoint:
        return WorkflowCheckpoint(
            any_of=tuple(
                WorkflowCheckpointClause(
                    inventory_all=tuple(
                        InventoryThreshold(item=item, quantity=count)
                        for item, count in option.items()
                    )
                )
                for option in items
            )
        )

    return {
        ("craft", "iron_pickaxe"): alternatives({"iron_pickaxe": 1}, {"iron_ingot": 3}),
        ("acquire", "water_bucket"): alternatives(
            {"water_bucket": 1}, {"bucket": 1}, {"iron_ingot": 3}
        ),
        ("acquire", "obsidian"): alternatives(
            {"obsidian": 10},
            {"diamond_pickaxe": 1, "water_bucket": 1},
            {"netherite_pickaxe": 1, "water_bucket": 1},
        ),
    }


def _inventory(values: Mapping[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item, count in values.items():
        key = _resource_id(item)
        result[key] = max(result.get(key, 0), count)
    return result


def _goal_contract(goal: GoalSpec) -> str:
    data = goal.model_dump(mode="json")
    predicates = []
    for predicate in data["success_predicates"]:
        if predicate["kind"] == "inventory_at_least":
            continue
        predicates.append(json.dumps(predicate, sort_keys=True))
    for item, quantity in _goal_inventory(goal).items():
        predicates.append(
            json.dumps(
                {"kind": "inventory_at_least", "item": item, "quantity": quantity}, sort_keys=True
            )
        )
    data["success_predicates"] = sorted(set(predicates))
    return json.dumps(data, sort_keys=True)


def _goal_inventory(goal: GoalSpec) -> dict[str, int]:
    result: dict[str, int] = {}
    for predicate in goal.success_predicates:
        if isinstance(predicate, InventoryAtLeast):
            item = _resource_id(predicate.item)
            result[item] = max(result.get(item, 0), predicate.quantity)
    return result


def validate_mission_plan(
    mission: MissionSpec,
    *,
    reference: MissionSpec,
    initial_inventory: Mapping[str, int],
    requirements: Mapping[tuple[str, str], WorkflowCheckpoint] | None = None,
) -> tuple[PlanningIssue, ...]:
    """Check fixed authority and necessary inputs without rewriting the model DAG.

    Ancestor postconditions are conditional evidence for a later eligible goal.
    This is not a simulation of material consumption or proof of executability.
    """
    expected = {(o.goal.intent, o.goal.target): o for o in reference.objectives}
    if len(expected) != len(reference.objectives):
        raise ValueError("planning reference must have distinct intent/target keys")
    actual = {(o.goal.intent, o.goal.target): o for o in mission.objectives}
    if (
        mission.mission_id != reference.mission_id
        or len(mission.objectives) != len(reference.objectives)
        or len(actual) != len(mission.objectives)
        or set(actual) != set(expected)
        or any(obj.required != expected[key].required for key, obj in actual.items())
        or mission.allowed_domains != reference.allowed_domains
        or mission.completion_rule != reference.completion_rule
        or mission.completion_predicates != reference.completion_predicates
    ):
        return (
            PlanningIssue(
                code="PLAN_SCOPE_MISMATCH", message="计划必须保留已授权的全部目标与完成条件。"
            ),
        )
    if (
        mission.budget != reference.budget
        or mission.execution != reference.execution
        or mission.autonomy != reference.autonomy
        or any(obj.budget != expected[key].budget for key, obj in actual.items())
    ):
        return (
            PlanningIssue(
                code="PLAN_AUTHORITY_MISMATCH", message="计划不得改动已授权的预算或执行策略。"
            ),
        )
    issues = [
        PlanningIssue(
            code="PLAN_GOAL_MISMATCH",
            message="目标参数或成功谓词与授权契约不符。",
            objective_id=obj.objective_id,
        )
        for key, obj in actual.items()
        if _goal_contract(obj.goal) != _goal_contract(expected[key].goal)
    ]
    if issues:
        return tuple(issues)

    by_id = {o.objective_id: o for o in mission.objectives}
    ancestors: dict[str, set[str]] = {}

    def upstream(objective_id: str) -> set[str]:
        if objective_id not in ancestors:
            found: set[str] = set()
            for parent in by_id[objective_id].dependencies:
                found.add(parent)
                found.update(upstream(parent))
            ancestors[objective_id] = found
        return ancestors[objective_id]

    outputs = {obj.objective_id: _goal_inventory(obj.goal) for obj in mission.objectives}

    def known_before(objective_id: str) -> dict[str, int]:
        known = _inventory(initial_inventory)
        for parent in upstream(objective_id):
            for item, count in outputs[parent].items():
                known[item] = max(known.get(item, 0), count)
        return known

    contracts = nether_plan_inventory_requirements() if requirements is None else requirements
    for key, obj in actual.items():
        contract = contracts.get(key)
        if contract is None:
            continue
        if any(option.maximum_y is not None for option in contract.any_of):
            raise ValueError("inventory planning contracts cannot contain position conditions")
        known = known_before(obj.objective_id)
        if any(
            all(known.get(_resource_id(i.item), 0) >= i.quantity for i in option.inventory_all)
            for option in contract.any_of
        ):
            continue
        suppliers = tuple(
            sorted(
                other.objective_id
                for other in mission.objectives
                if other.objective_id != obj.objective_id
                and other.objective_id not in upstream(obj.objective_id)
                and obj.objective_id not in upstream(other.objective_id)
                and any(
                    outputs[other.objective_id].get(_resource_id(item.item), 0) >= item.quantity
                    for option in contract.any_of
                    for item in option.inventory_all
                )
            )
        )
        issues.append(
            PlanningIssue(
                code="MISSING_WORKFLOW_INPUTS",
                objective_id=obj.objective_id,
                message="初始库存和前置目标未提供必要物品；请补充资源依赖，保持预算和任务范围。",
                required_any_of=contract.any_of,
                candidate_dependencies=suppliers,
            )
        )
    descent = actual.get(("craft", "diamond_pickaxe"))
    water = actual.get(("acquire", "water_bucket"))
    if descent is not None and water is not None:
        known = known_before(descent.objective_id)
        provisioned = (
            known.get(_resource_id("water_bucket"), 0) >= water.goal.quantity
            or known.get(_resource_id("diamond_pickaxe"), 0) >= descent.goal.quantity
            or known.get(_resource_id("diamond"), 0) >= 3 * descent.goal.quantity
        )
        shores = [
            predicate
            for objective in reference.objectives
            if objective.goal.intent == "travel" and objective.goal.target == "surface-water-access"
            for predicate in objective.goal.success_predicates
            if isinstance(predicate, LocationReached)
        ]
        # A pre-descent visit is stale. A return must follow descent and precede
        # water, and its entire accepted location region must prove the shore.
        returned = any(
            dist((position.x, position.y, position.z), (shore.x, shore.y, shore.z))
            + position.tolerance
            <= shore.tolerance
            for parent in upstream(water.objective_id)
            if by_id[parent].goal.intent == "travel" and descent.objective_id in upstream(parent)
            for position in by_id[parent].goal.success_predicates
            if isinstance(position, LocationReached)
            for shore in shores
        )
        if not provisioned and not returned:
            issues.append(
                PlanningIssue(
                    code="MISSING_ACCESS_PROVISION",
                    objective_id=descent.objective_id,
                    message=NETHER_DESCENT_ACCESS_RULE,
                    candidate_dependencies=(water.objective_id,),
                )
            )
    return tuple(issues)
