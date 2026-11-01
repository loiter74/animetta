"""Compile small model route drafts while retaining host-owned task authority."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.mission.models import MissionObjective, MissionSpec
from animetta.tools.minecraft.skill.candidate import SkillCandidate, compile_candidate
from animetta.tools.minecraft.skill.independent_validation import goal_postconditions
from animetta.tools.minecraft.skill.ir import (
    ActionStep,
    BranchStep,
    ParameterSpec,
    Predicate,
    RepeatStep,
    SkillProgram,
    SkillStep,
)
from animetta.tools.minecraft.survival.mainline import build_nether_portal_mission
from animetta.tools.minecraft.survival.workflows import (
    InventoryThreshold,
    WorkflowCheckpoint,
    WorkflowCheckpointClause,
)
from animetta.tools.minecraft.voyager.budget import BudgetUsage

from .minecraft_learning import build_bounded_learning_portal_mission
from .minecraft_planning import (
    inventory_input_options,
    nether_plan_inventory_requirements,
    validate_mission_plan,
)

CONTRACT_ID = "bounded_route_learning_portal_v2"
RouteTask = Literal[
    "iron",
    "iron-pickaxe",
    "water-return",
    "water-bucket",
    "ignition",
    "diamond-pickaxe",
    "obsidian",
    "return-home",
    "portal",
]


class _Draft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SmallSkillDraft(_Draft):
    task: RouteTask
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,127}$")
    steps: tuple[SkillStep, ...] = Field(min_length=1, max_length=128)
    preconditions: tuple[Predicate, ...] = ()


class RouteDraft(_Draft):
    route: tuple[RouteTask, ...] = Field(min_length=1, max_length=9)
    budget_overrides: dict[RouteTask, BudgetUsage] = Field(default_factory=dict)
    skill: SmallSkillDraft | None = None

    @model_validator(mode="after")
    def _bounded_route(self) -> Self:
        if len(self.route) != len(set(self.route)) or self.route[-1] != "portal":
            raise ValueError("route must contain unique tasks and end with portal")
        if set(self.budget_overrides) - set(self.route):
            raise ValueError("budget override refers to an unselected task")
        if self.skill is not None and self.skill.task not in self.route:
            raise ValueError("skill must belong to a selected preparation task")
        return self


class RoutePlanningError(ValueError):
    def __init__(self, issues: list[dict]) -> None:
        self.issues = tuple(issues)
        super().__init__(json.dumps(issues, ensure_ascii=False, default=str))


def _actions(steps: tuple[object, ...]) -> Iterator[ActionStep]:
    for step in steps:
        if isinstance(step, ActionStep):
            yield step
        elif isinstance(step, BranchStep):
            yield from _actions(step.then_steps)
            yield from _actions(step.else_steps)
        elif isinstance(step, RepeatStep):
            yield from _actions(step.steps)


def _skill_parameters(home: tuple[float, float, float]) -> tuple[ParameterSpec, ...]:
    return (
        ParameterSpec(name="target", value_type="string"),
        ParameterSpec(name="quantity", value_type="integer"),
        *(
            ParameterSpec(
                name=f"home_{axis}", value_type="integer" if type(value) is int else "number"
            )
            for axis, value in zip("xyz", home, strict=True)
        ),
    )


def _route_inventory_requirements() -> dict[tuple[str, str], WorkflowCheckpoint]:
    requirements = nether_plan_inventory_requirements()
    requirements[("build", "nether_portal")] = WorkflowCheckpoint(
        any_of=(
            WorkflowCheckpointClause(
                inventory_all=(
                    InventoryThreshold(item="obsidian", quantity=10),
                    InventoryThreshold(item="flint_and_steel", quantity=1),
                )
            ),
        )
    )
    return requirements


def route_prompt_context(
    *,
    mission_id: str,
    home: tuple[float, float, float],
    observation: Observation,
    manifest: RuntimeManifest,
) -> dict:
    """Send routing facts and capability schemas, keeping raw voxel evidence outside the prompt."""
    catalogue = build_nether_portal_mission(mission_id=mission_id, home=home)
    requirements = _route_inventory_requirements()
    supplier_goals = {obj.objective_id: obj.goal for obj in catalogue.objectives}
    raw = observation.model_dump(mode="json")
    blocks = raw.get("visible_blocks", [])
    return {
        "route_schema": RouteDraft.model_json_schema(),
        "catalogue": [
            {
                "task": obj.objective_id,
                "goal": obj.goal.model_dump(mode="json"),
                "default_budget": obj.budget.model_dump(mode="json"),
                "default_workflow_inputs": [
                    option.model_dump(mode="json")
                    for option in inventory_input_options(
                        requirements[(obj.goal.intent, obj.goal.target)],
                        known_inventory=observation.inventory,
                        supplier_goals=supplier_goals,
                        consumer_id=obj.objective_id,
                    )
                ]
                if (obj.goal.intent, obj.goal.target) in requirements
                else [],
            }
            for obj in sorted(catalogue.objectives, key=lambda obj: obj.objective_id)
        ],
        "parent_budget": catalogue.budget.model_dump(mode="json"),
        "inventory_planning_rules": (
            "default_workflow_inputs 是默认流程的必要库存条件，任一组 inventory_all 全部满足即可。"
            "missing_quantity 按初始库存计算；路线中较早目标的成功谓词也可提供条件。"
            "supplier_tasks 是可选目录任务，不是已满足的依赖或可直接添加的 DAG 边；"
            "供给任务须排在使用者之前，并满足自身前置条件。不能复制任务或形成依赖环。"
            "空 supplier_tasks 表示没有目录供给证明；不得虚构新任务。"
            "生成小技能只替换所属目标的默认流程，不改变该目标的成功谓词或预算。"
            "这些条件不模拟物品消耗，也不保证运行成功；最终仍由实际执行和验证器判定。"
        ),
        "observation": {
            "observation_id": observation.observation_id,
            "position": raw.get("position"),
            "inventory": observation.inventory,
            "health": observation.health,
            "food": observation.food,
            "dimension": observation.environment.get("dimension"),
            "biome": observation.environment.get("biome"),
            "visible_block_types": sorted({block["block_id"] for block in blocks}),
            "nearby_block_samples": blocks[:16],
        },
        "host_skill_parameters": [p.model_dump(mode="json") for p in _skill_parameters(home)],
        "host_skill_bindings": {
            f"home_{axis}": value for axis, value in zip("xyz", home, strict=True)
        },
        "preparation_capabilities": [
            {
                "name": cap.name,
                "parameters_schema": cap.parameters_schema,
                "minimum_cost": cap.maximum_cost.model_dump(
                    mode="json", exclude={"protected_items"}
                ),
            }
            for cap in manifest.capabilities
            if cap.effect_class != "read_only" and cap.name != "ignite_portal"
        ],
    }


def compile_route_draft(
    draft: RouteDraft,
    *,
    mission_id: str,
    home: tuple[float, float, float],
    origin: tuple[int, int, int],
    manifest: RuntimeManifest,
    initial_inventory: dict[str, int],
) -> MissionSpec:
    """Resolve model choices against the existing catalogue and immutable endpoint."""
    catalogue = build_nether_portal_mission(mission_id=mission_id, home=home)
    authority = build_bounded_learning_portal_mission(
        mission_id=mission_id, home=home, origin=origin
    )
    by_id = {objective.objective_id: objective for objective in catalogue.objectives}
    objectives: list[MissionObjective] = []
    issues: list[dict] = []
    for task in draft.route:
        original = by_id[task]
        constraints = {**original.goal.constraints, "learning_mode": "model_generated_only"}
        constraints.update({f"home_{axis}": value for axis, value in zip("xyz", home, strict=True)})
        goal = original.goal.model_copy(update={"constraints": constraints})
        budget = draft.budget_overrides.get(task, original.budget)
        if draft.skill is not None and draft.skill.task == task:
            if goal.intent not in {"acquire", "craft"}:
                issues.append({"code": "SKILL_SCOPE_FORBIDDEN", "task": task})
            else:
                actions = tuple(_actions(draft.skill.steps))
                if any(action.capability == "ignite_portal" for action in actions):
                    issues.append({"code": "SKILL_PORTAL_GEOMETRY_FORBIDDEN", "task": task})
                if any(action.maximum_cost is None for action in actions):
                    issues.append({"code": "SKILL_ACTION_ALLOCATION_REQUIRED", "task": task})
                program = SkillProgram(
                    name=draft.skill.name,
                    parameters=_skill_parameters(home),
                    preconditions=draft.skill.preconditions,
                    steps=draft.skill.steps,
                    postconditions=goal_postconditions(goal),
                )
                candidate = SkillCandidate(program=program)
                goal = goal.model_copy(
                    update={
                        "constraints": {
                            **constraints,
                            "skill_candidate": candidate.model_dump(mode="json"),
                        }
                    }
                )
                try:
                    compile_candidate(
                        candidate,
                        manifest=manifest,
                        budget=authority.budget.model_copy(update=budget.model_dump()),
                        goal=goal,
                        source_command_id="route-preflight-only",
                    )
                except ValueError as exc:
                    issues.append(
                        {"code": "SKILL_COMPILE_FAILED", "task": task, "message": str(exc)}
                    )
        objectives.append(
            original.model_copy(
                update={
                    "goal": goal,
                    "budget": budget,
                    "dependencies": (objectives[-1].objective_id,) if objectives else (),
                }
            )
        )
    try:
        mission = MissionSpec.model_validate(
            {**authority.model_dump(), "objectives": tuple(objectives)}
        )
    except ValueError as exc:
        issues.append({"code": "ROUTE_BUDGET_OR_AUTHORITY_INVALID", "message": str(exc)})
        raise RoutePlanningError(issues) from exc
    requirements = _route_inventory_requirements()
    if draft.skill is not None:
        learned = by_id[draft.skill.task].goal
        requirements.pop((learned.intent, learned.target), None)
    for issue in validate_mission_plan(
        mission,
        reference=mission,
        initial_inventory=initial_inventory,
        requirements=requirements,
        supplier_goals={task: obj.goal for task, obj in by_id.items()},
    ):
        if issue.code == "MISSING_WORKFLOW_INPUTS" and issue.objective_id == "portal":
            # Preserve the route contract's per-item error codes using the shared resolver.
            for option in issue.input_options:
                for item in option.inventory_all:
                    if item.missing_quantity:
                        issues.append(
                            {
                                "code": "MISSING_PORTAL_INPUT",
                                "task": "portal",
                                **item.model_dump(mode="json"),
                                "item": item.item.removeprefix("minecraft:"),
                                "message": issue.message,
                            }
                        )
        else:
            issues.append(issue.model_dump(mode="json"))
    if issues:
        raise RoutePlanningError(issues)
    return mission
