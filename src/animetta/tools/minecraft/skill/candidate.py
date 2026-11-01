"""Compile model-supplied candidates without granting revision trust."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from animetta.tools.gamebot.contracts.v2 import RuntimeManifest
from animetta.tools.minecraft.voyager.budget import ExecutionBudget
from animetta.tools.minecraft.voyager.goal_models import GoalSpec

from .applicability import applicability_for_goal
from .ir import SkillDefinition, SkillProgram, SkillRevision, compile_skill_program


class SkillCandidate(BaseModel):
    """One typed proposal; successful execution alone does not establish trust."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    program: SkillProgram


def compile_candidate(
    candidate: SkillCandidate,
    *,
    manifest: RuntimeManifest,
    budget: ExecutionBudget,
    goal: GoalSpec,
    source_command_id: str,
) -> tuple[SkillRevision, dict[str, object]]:
    compiled = compile_skill_program(
        candidate.program,
        capabilities={
            capability.name: {
                "parameters_schema": capability.parameters_schema,
                "maximum_cost": capability.maximum_cost.model_dump(
                    mode="json", exclude={"protected_items"}
                ),
            }
            for capability in manifest.capabilities
        },
        budget=budget,
    )
    revision = compiled.to_revision(
        SkillDefinition(
            definition_id=f"generated:{goal.intent}:{goal.target}",
            name=candidate.program.name,
            description="Model-generated bounded candidate; independent validation deferred",
        ),
        source_command_id=source_command_id,
    )
    applicability = applicability_for_goal(revision, goal)
    bindings: dict[str, object] = {}
    for binding in applicability.parameter_bindings:
        if binding.source == "goal_target":
            value = goal.target
        elif binding.source == "goal_quantity":
            value = goal.quantity
        else:
            value = goal.constraints[binding.constraint_key]
        parameter = next(p for p in revision.program.parameters if p.name == binding.parameter)
        valid = {
            "string": isinstance(value, str),
            "integer": type(value) is int,
            "number": type(value) in (int, float),
            "boolean": type(value) is bool,
        }[parameter.value_type]
        if not valid:
            raise ValueError(f"INVALID_SKILL_BINDING: {parameter.name}")
        bindings[binding.parameter] = value
    return revision, bindings
