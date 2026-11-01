"""Declarative Skill IR schema and static compiler tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from animetta.tools.minecraft.skill.ir import (
    SkillDefinition,
    SkillIRValidationError,
    SkillProgram,
    compile_skill_program,
)
from animetta.tools.minecraft.voyager.budget import BudgetUsage, ExecutionBudget

CAPABILITIES = {
    "collect": {
        "parameters_schema": {
            "type": "object",
            "properties": {
                "block_type": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["block_type", "count"],
            "additionalProperties": False,
        },
        "maximum_cost": BudgetUsage(max_actions=1, max_travel_distance=16, max_blocks_changed=4),
    }
}

BUDGET = ExecutionBudget(
    queue_timeout_ms=1_000,
    execution_timeout_ms=10_000,
    max_actions=8,
    max_strategy_attempts=4,
    max_travel_distance=128,
    max_blocks_changed=32,
    max_damage_taken=4,
)


def valid_program_payload() -> dict:
    return {
        "schema_version": "1",
        "name": "collect_logs",
        "parameters": [
            {"name": "target", "value_type": "string", "required": True},
            {"name": "count", "value_type": "integer", "required": True},
        ],
        "steps": [
            {
                "kind": "action",
                "step_id": "collect-1",
                "capability": "collect",
                "parameters": {
                    "block_type": {"kind": "goal_input", "name": "target"},
                    "count": {"kind": "goal_input", "name": "count"},
                },
            },
            {
                "kind": "branch",
                "step_id": "health-branch",
                "condition": {
                    "op": "gte",
                    "left": {"kind": "observation", "path": "health"},
                    "right": {"kind": "literal", "value": 5},
                },
                "then_steps": [],
                "else_steps": [{"kind": "fail", "step_id": "unsafe", "code": "LOW_HEALTH"}],
            },
            {
                "kind": "repeat",
                "step_id": "bounded-retry",
                "max_iterations": 2,
                "steps": [],
            },
        ],
        "postconditions": [
            {
                "op": "gte",
                "left": {"kind": "observation", "path": "inventory.oak_log"},
                "right": {"kind": "goal_input", "name": "count"},
            }
        ],
        "portability": {"portable": True, "dimensions": ["minecraft:overworld"]},
    }


def test_skill_ir_is_normalized_content_addressed_and_statically_costed() -> None:
    program = SkillProgram.model_validate(valid_program_payload())
    compiled = compile_skill_program(program, capabilities=CAPABILITIES, budget=BUDGET)
    definition = SkillDefinition(
        definition_id="skill:collect_logs",
        name="collect_logs",
        description="Collect a bounded quantity of logs",
    )
    revision = compiled.to_revision(definition, source_command_id="command-1")

    assert compiled.static_cost.max_actions == 1
    assert compiled.static_cost.max_travel_distance == 16
    assert revision.revision_hash == program.canonical_hash
    assert revision.program is program


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda p: p.update({"code": "process.exit(0)"}), "extra"),
        (
            lambda p: p["steps"].__setitem__(
                0,
                {
                    "kind": "action",
                    "step_id": "collect-1",
                    "capability": {"kind": "goal_input", "name": "tool"},
                    "parameters": {},
                },
            ),
            "capability",
        ),
        (
            lambda p: p["steps"][0]["parameters"].update(
                {"count": {"kind": "goal_input", "name": "missing"}}
            ),
            "unbound goal input",
        ),
        (
            lambda p: p["steps"][0]["parameters"].update(
                {"count": {"kind": "literal", "value": "many"}}
            ),
            "expects integer",
        ),
        (
            lambda p: p["steps"].append({"kind": "call", "step_id": "recursive", "skill": "self"}),
            "union_tag_invalid",
        ),
        (
            lambda p: p["steps"].append({"kind": "repeat", "step_id": "forever", "steps": []}),
            "max_iterations",
        ),
        (
            lambda p: p["postconditions"].__setitem__(
                0,
                {
                    "op": "eq",
                    "left": {"kind": "observation", "path": "raw_bot.secret"},
                    "right": {"kind": "literal", "value": 1},
                },
            ),
            "forbidden observation field",
        ),
    ],
)
def test_invalid_or_unbounded_ir_is_rejected(mutation, match: str) -> None:
    payload = valid_program_payload()
    mutation(payload)
    try:
        program = SkillProgram.model_validate(payload)
        compile_skill_program(program, capabilities=CAPABILITIES, budget=BUDGET)
    except (ValidationError, SkillIRValidationError) as exc:
        assert match.lower() in str(exc).lower()
    else:
        raise AssertionError("invalid Skill IR must be rejected")


def test_static_cost_above_parent_budget_is_rejected() -> None:
    program = SkillProgram.model_validate(valid_program_payload())
    tiny = BUDGET.model_copy(update={"max_actions": 0})

    with pytest.raises(SkillIRValidationError, match="static cost exceeds"):
        compile_skill_program(program, capabilities=CAPABILITIES, budget=tiny)


RUNTIME_SHAPED_CAPABILITIES = {
    "collect": {
        "parameters_schema": CAPABILITIES["collect"]["parameters_schema"],
        # Real R100 manifest shape: admission is atomic, work quotas come from callers.
        "maximum_cost": BudgetUsage(max_actions=1),
    }
}


def explicit_cost_program(steps: list[dict]) -> dict:
    return {
        "schema_version": "1",
        "name": "granted_collect",
        "steps": steps,
        "postconditions": [
            {
                "op": "gte",
                "left": {"kind": "observation", "path": "inventory.oak_log"},
                "right": {"kind": "literal", "value": 1},
            }
        ],
    }


def collect_step(step_id: str, maximum_cost: dict | None = None) -> dict:
    step = {
        "kind": "action",
        "step_id": step_id,
        "capability": "collect",
        "parameters": {
            "block_type": {"kind": "literal", "value": "oak_log"},
            "count": {"kind": "literal", "value": 1},
        },
    }
    if maximum_cost is not None:
        step["maximum_cost"] = maximum_cost
    return step


def test_explicit_maximum_cost_carries_caller_granted_work_quota_into_static_cost() -> None:
    granted = {"max_actions": 1, "max_travel_distance": 64.0, "max_blocks_changed": 8}
    payload = explicit_cost_program([collect_step("collect-1", granted)])
    program = SkillProgram.model_validate(payload)

    compiled = compile_skill_program(
        program, capabilities=RUNTIME_SHAPED_CAPABILITIES, budget=BUDGET
    )
    revision = compiled.to_revision(
        SkillDefinition(
            definition_id="skill:granted_collect", name="granted_collect", description=""
        ),
        source_command_id="command-2",
    )

    assert compiled.static_cost == BudgetUsage(
        max_actions=1, max_travel_distance=64.0, max_blocks_changed=8
    )
    assert revision.static_cost == compiled.static_cost
    assert revision.program.steps[0].maximum_cost == BudgetUsage(
        max_actions=1, max_travel_distance=64.0, max_blocks_changed=8
    )
    round_tripped = SkillProgram.model_validate(program.model_dump(mode="json"))
    assert round_tripped.canonical_hash == program.canonical_hash
    assert round_tripped.steps[0].maximum_cost == BudgetUsage(
        max_actions=1, max_travel_distance=64.0, max_blocks_changed=8
    )


def test_omitted_maximum_cost_keeps_legacy_serialization_and_hash_byte_shape() -> None:
    legacy_payload = valid_program_payload()
    assert all("maximum_cost" not in step for step in legacy_payload["steps"])
    legacy = SkillProgram.model_validate(legacy_payload)
    explicit_none = SkillProgram.model_validate(
        {
            **legacy_payload,
            "steps": [dict(legacy_payload["steps"][0], maximum_cost=None)]
            + legacy_payload["steps"][1:],
        }
    )

    legacy_dump = legacy.model_dump(mode="json")

    assert all("maximum_cost" not in step for step in legacy_dump["steps"])
    assert legacy.canonical_hash == explicit_none.canonical_hash
    assert (
        legacy.canonical_hash
        == SkillProgram.model_validate(legacy.model_dump(mode="json")).canonical_hash
    )


def test_explicit_maximum_cost_under_indivisible_manifest_charge_is_rejected() -> None:
    under_atomic = SkillProgram.model_validate(
        explicit_cost_program([collect_step("collect-1", {"max_actions": 0})])
    )

    with pytest.raises(SkillIRValidationError, match="indivisible charge: max_actions"):
        compile_skill_program(under_atomic, capabilities=RUNTIME_SHAPED_CAPABILITIES, budget=BUDGET)

    consumable = {
        "collect": {
            "parameters_schema": CAPABILITIES["collect"]["parameters_schema"],
            "maximum_cost": BudgetUsage(
                max_actions=1,
                max_strategy_attempts=1,
                max_damage_taken=2.0,
                resource_consumption={"oak_log": 2},
            ),
        }
    }
    under_resource = SkillProgram.model_validate(
        explicit_cost_program(
            [
                collect_step(
                    "collect-1",
                    {
                        "max_actions": 1,
                        "max_strategy_attempts": 1,
                        "max_damage_taken": 2.0,
                        "resource_consumption": {"oak_log": 1},
                    },
                )
            ]
        )
    )

    with pytest.raises(SkillIRValidationError, match="indivisible resource: oak_log"):
        compile_skill_program(under_resource, capabilities=consumable, budget=BUDGET)

    honest = SkillProgram.model_validate(
        explicit_cost_program(
            [
                collect_step(
                    "collect-1",
                    {
                        "max_actions": 1,
                        "max_strategy_attempts": 1,
                        "max_damage_taken": 2.0,
                        "resource_consumption": {"oak_log": 2},
                    },
                )
            ]
        )
    )
    compiled = compile_skill_program(
        honest,
        capabilities=consumable,
        budget=BUDGET.model_copy(update={"resource_consumption": {"oak_log": 2}}),
    )
    assert compiled.static_cost.resource_consumption == {"oak_log": 2}


def test_explicit_costs_still_scale_in_repeats_and_branches_and_respect_parent_budget() -> None:
    granted = {"max_actions": 1, "max_travel_distance": 64.0, "max_blocks_changed": 8}
    repeated = SkillProgram.model_validate(
        explicit_cost_program(
            [
                {
                    "kind": "repeat",
                    "step_id": "twice",
                    "max_iterations": 2,
                    "steps": [collect_step("collect-1", granted)],
                }
            ]
        )
    )
    branched = SkillProgram.model_validate(
        explicit_cost_program(
            [
                {
                    "kind": "branch",
                    "step_id": "route",
                    "condition": {
                        "op": "gte",
                        "left": {"kind": "observation", "path": "health"},
                        "right": {"kind": "literal", "value": 5},
                    },
                    "then_steps": [collect_step("near-collect", granted)],
                    "else_steps": [
                        collect_step("far-collect", {"max_actions": 1, "max_travel_distance": 32.0})
                    ],
                }
            ]
        )
    )

    repeated_compiled = compile_skill_program(
        repeated, capabilities=RUNTIME_SHAPED_CAPABILITIES, budget=BUDGET
    )
    branched_compiled = compile_skill_program(
        branched, capabilities=RUNTIME_SHAPED_CAPABILITIES, budget=BUDGET
    )

    assert repeated_compiled.static_cost == BudgetUsage(
        max_actions=2, max_travel_distance=128.0, max_blocks_changed=16
    )
    assert branched_compiled.static_cost == BudgetUsage(
        max_actions=1, max_travel_distance=64.0, max_blocks_changed=8
    )
    with pytest.raises(SkillIRValidationError, match="static cost exceeds"):
        compile_skill_program(
            repeated,
            capabilities=RUNTIME_SHAPED_CAPABILITIES,
            budget=BUDGET.model_copy(update={"max_travel_distance": 100.0}),
        )
