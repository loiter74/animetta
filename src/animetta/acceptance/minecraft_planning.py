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
    nether_preparation_workflows,
)
from animetta.tools.minecraft.voyager.goal_models import GoalSpec, InventoryAtLeast, LocationReached
from animetta.tools.minecraft.voyager.goal_verifier import _resource_id

NETHER_DESCENT_ACCESS_RULE = (
    "采铁和采钻会改变位置，采矿前访问过岸边不能证明采矿后仍可取水。"
    "采铁作为取水前置时，应在采铁之后、取水之前执行已授权的岸边返回目标；"
    "钻石工作流下矿前应备水，或明确安排下降后返回同岸边再取水。"
    "已具水桶、铁目标已满足或已有本地钻石材料时，按已知库存跳过不必要的顺序。"
    "目标目录不是执行顺序；修复只能在授权目录中选择、重排或复用目标并调整依赖，"
    "必要时移除失效旧边避免成环，禁止复制目标或创建目录外返岸目标，不得改动预算。"
    "candidate_dependency_paths 只表示已有目标之间应满足的先后，不是追加动作。"
    "location_options.supplier_tasks是目录中的位置供给选项，不是可直接添加的依赖边；"
    "须选择供给目标并排在失效位置的采矿之后、取水之前。"
    "工作台属于原地点的设施，不随铁锭移动；零方块预算的铁镐制作应在离开采铁工作台前完成。"
    "就绪目标按优先级降序、同优先级按目录顺序执行，也可通过合法优先级保留设施访问。"
)


class InventoryInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    item: str
    quantity: int
    available_quantity: int
    missing_quantity: int
    supplier_tasks: tuple[str, ...] = ()


class InventoryInputOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    inventory_all: tuple[InventoryInput, ...]

    @property
    def satisfied(self) -> bool:
        return all(item.missing_quantity == 0 for item in self.inventory_all)


class LocationInputOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    region: LocationReached
    supplier_tasks: tuple[str, ...]


class PlanningIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    objective_id: str | None = None
    required_any_of: tuple[WorkflowCheckpointClause, ...] = ()
    candidate_dependencies: tuple[str, ...] = ()
    # Diagnostic orderings of existing objectives only; not a new topological rule.
    candidate_dependency_paths: tuple[tuple[str, ...], ...] = ()
    # Catalogue choices, not edges that may safely be added to the current DAG.
    input_options: tuple[InventoryInputOption, ...] = ()
    location_options: tuple[LocationInputOption, ...] = ()


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


def _location_within(position: LocationReached, region: LocationReached) -> bool:
    return (
        dist((position.x, position.y, position.z), (region.x, region.y, region.z))
        + position.tolerance
        <= region.tolerance
    )


def surface_access_input_options(
    supplier_goals: Mapping[str, GoalSpec],
) -> tuple[LocationInputOption, ...]:
    """Describe catalogue location proofs; neither select tasks nor infer live reachability."""
    regions = [
        predicate
        for goal in supplier_goals.values()
        if goal.intent == "travel" and goal.target == "surface-water-access"
        for predicate in goal.success_predicates
        if isinstance(predicate, LocationReached)
    ]
    return tuple(
        LocationInputOption(
            region=region,
            supplier_tasks=tuple(
                sorted(
                    task
                    for task, goal in supplier_goals.items()
                    if goal.intent == "travel"
                    and any(
                        isinstance(position, LocationReached) and _location_within(position, region)
                        for position in goal.success_predicates
                    )
                )
            ),
        )
        for region in regions
    )


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


def inventory_input_options(
    contract: WorkflowCheckpoint,
    *,
    known_inventory: Mapping[str, int],
    supplier_goals: Mapping[str, GoalSpec],
    consumer_id: str,
) -> tuple[InventoryInputOption, ...]:
    """Describe necessary inventory and conditional suppliers without planning a DAG.

    Quantities are lower bounds, never additive receipts or a consumption simulation.
    Suppliers may require other inputs or reordering; they are not executable recipes.
    """
    if any(option.maximum_y is not None for option in contract.any_of):
        raise ValueError("inventory planning contracts cannot contain position conditions")
    known = _inventory(known_inventory)
    outputs = {
        task: _goal_inventory(goal) for task, goal in supplier_goals.items() if task != consumer_id
    }
    options = []
    for option in contract.any_of:
        required: dict[str, int] = {}
        for threshold in option.inventory_all:
            item = _resource_id(threshold.item)
            required[item] = max(required.get(item, 0), threshold.quantity)
        inputs = []
        for item, quantity in required.items():
            available = known.get(item, 0)
            inputs.append(
                InventoryInput(
                    item=item,
                    quantity=quantity,
                    available_quantity=available,
                    missing_quantity=max(0, quantity - available),
                    supplier_tasks=tuple(
                        sorted(
                            task
                            for task, inventory in outputs.items()
                            if available < quantity and inventory.get(item, 0) >= quantity
                        )
                    ),
                )
            )
        options.append(InventoryInputOption(inventory_all=tuple(inputs)))
    return tuple(options)


def _scheduled_objective_ids(mission: MissionSpec) -> tuple[str, ...]:
    # Match the coordinator's priority/ordinal choice among ready objectives.
    pending = sorted(mission.objectives, key=lambda obj: -obj.priority)
    completed: set[str] = set()
    order = []
    while pending:
        objective = next(obj for obj in pending if set(obj.dependencies) <= completed)
        order.append(objective.objective_id)
        completed.add(objective.objective_id)
        pending.remove(objective)
    return tuple(order)


def validate_mission_plan(
    mission: MissionSpec,
    *,
    reference: MissionSpec,
    initial_inventory: Mapping[str, int],
    requirements: Mapping[tuple[str, str], WorkflowCheckpoint] | None = None,
    supplier_goals: Mapping[str, GoalSpec] | None = None,
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
    available_goals = (
        {objective.objective_id: objective.goal for objective in mission.objectives}
        if supplier_goals is None
        else supplier_goals
    )
    for key, obj in actual.items():
        contract = contracts.get(key)
        if contract is None:
            continue
        known = known_before(obj.objective_id)
        options = inventory_input_options(
            contract,
            known_inventory=known,
            supplier_goals=available_goals,
            consumer_id=obj.objective_id,
        )
        if any(option.satisfied for option in options):
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
                message=(
                    "初始库存和前置目标未提供必要物品；input_options 列出目录中的供给任务。"
                    "在原预算内选择可满足的一组前置条件，供给任务必须先于当前目标执行。"
                    "已选但排在后面的任务应重排并移除失效旧边，不可复制任务或添加成环依赖。"
                    "供给任务仍需满足自身前置条件；空 supplier_tasks 表示目录没有可证明的供给。"
                ),
                required_any_of=contract.any_of,
                candidate_dependencies=suppliers,
                input_options=options,
            )
        )
    iron_kit = actual.get(("acquire", "nether_iron_kit"))
    pickaxe = actual.get(("craft", "iron_pickaxe"))
    if (
        iron_kit is not None
        and pickaxe is not None
        and pickaxe.budget.max_blocks_changed == 0
        and iron_kit.objective_id in upstream(pickaxe.objective_id)
        and known_before(pickaxe.objective_id).get(_resource_id("iron_pickaxe"), 0)
        < pickaxe.goal.quantity
    ):
        order = _scheduled_objective_ids(mission)
        between = order[order.index(iron_kit.objective_id) + 1 : order.index(pickaxe.objective_id)]
        mobile_workflows = {
            (workflow.intent, workflow.target)
            for workflow in nether_preparation_workflows()
            if any(step.maximum_cost.max_travel_distance > 0 for step in workflow.steps)
        }
        moving = []
        for objective_id in between:
            objective = by_id[objective_id]
            goal = objective.goal
            if (
                goal.intent not in {"travel", "build"}
                and (
                    goal.intent,
                    goal.target,
                )
                not in mobile_workflows
            ):
                continue
            known = known_before(objective_id)
            if (
                outputs[objective_id]
                and all(
                    isinstance(predicate, InventoryAtLeast) for predicate in goal.success_predicates
                )
                and all(
                    known.get(item, 0) >= quantity
                    for item, quantity in outputs[objective_id].items()
                )
            ):
                continue
            moving.append(objective)
        if moving:
            issues.append(
                PlanningIssue(
                    code="MISSING_WORKSTATION_ACCESS",
                    objective_id=pickaxe.objective_id,
                    message=(
                        "零方块预算不能在离开原工作台后另放工作台；请复用现有目标，"
                        "调整依赖或优先级，先完成本地铁镐制作，再执行会移动的目标。"
                    ),
                    candidate_dependency_paths=tuple(
                        (iron_kit.objective_id, pickaxe.objective_id, objective.objective_id)
                        for objective in moving
                    ),
                )
            )
    water = actual.get(("acquire", "water_bucket"))
    if water is not None:
        location_options = surface_access_input_options(available_goals)
        shores = [option.region for option in location_options]
        water_ancestors = upstream(water.objective_id)

        def returned_after(objective_id: str) -> bool:
            # Require the whole accepted location region to prove a fresh shore.
            return any(
                _location_within(position, shore)
                for parent in water_ancestors
                if by_id[parent].goal.intent == "travel" and objective_id in upstream(parent)
                for position in by_id[parent].goal.success_predicates
                if isinstance(position, LocationReached)
                for shore in shores
            )

        for key in (("acquire", "nether_iron_kit"), ("craft", "diamond_pickaxe")):
            mining = actual.get(key)
            if mining is None:
                continue
            iron = key == ("acquire", "nether_iron_kit")
            # Use the authorized catalogue even when its return task was omitted.
            # Inventory-only and standalone plans without a shore keep their scope.
            if iron and (not shores or mining.objective_id not in water_ancestors):
                continue
            known = known_before(mining.objective_id)
            postconditions = outputs[mining.objective_id]
            completed = bool(postconditions) and all(
                known.get(item, 0) >= quantity for item, quantity in postconditions.items()
            )
            provisioned = known.get(_resource_id("water_bucket"), 0) >= water.goal.quantity
            local_craft = (
                not iron and known.get(_resource_id("diamond"), 0) >= 3 * mining.goal.quantity
            )
            if completed or provisioned or local_craft or returned_after(mining.objective_id):
                continue
            suppliers = (
                tuple(
                    obj.objective_id
                    for obj in mission.objectives
                    if obj.goal.intent == "travel" and obj.goal.target == "surface-water-access"
                )
                if iron
                else (water.objective_id,)
            )
            issues.append(
                PlanningIssue(
                    code="MISSING_ACCESS_PROVISION",
                    objective_id=water.objective_id if iron else mining.objective_id,
                    message=NETHER_DESCENT_ACCESS_RULE,
                    candidate_dependencies=suppliers,
                    candidate_dependency_paths=(
                        tuple(
                            (mining.objective_id, shore, water.objective_id) for shore in suppliers
                        )
                        if iron
                        else ((water.objective_id, mining.objective_id),)
                    ),
                    location_options=location_options if iron else (),
                )
            )
    return tuple(issues)
