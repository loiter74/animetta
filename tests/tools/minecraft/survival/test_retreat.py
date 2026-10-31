"""Reactive retreat uses the original mission account and preserves its workflow."""

import json
from pathlib import Path

from pydantic import TypeAdapter

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.survival.registry import WorkflowRegistry
from animetta.tools.minecraft.survival.retreat import propose_retreat
from animetta.tools.minecraft.survival.workflows import iron_survival_workflow
from animetta.tools.minecraft.voyager.budget import ExecutionBudget
from animetta.tools.minecraft.voyager.goal_models import GoalSpec
from animetta.tools.minecraft.voyager.strategies.base import Complete
from animetta.tools.minecraft.voyager.strategies.fallback import FallbackStrategy
from animetta.tools.minecraft.voyager.strategies.mission import MissionStrategy

ROOT = Path(__file__).resolve().parents[4]
MESSAGES = json.loads((ROOT / "contracts/gamebot/v2/fixtures/golden.json").read_text("utf-8"))[
    "messages"
]


def observed(candidates=None):
    observation = Observation.model_validate(MESSAGES["Observation"])
    return observation.model_copy(
        update={
            "inventory": {},
            "environment": {
                "survival_retreat": {
                    "origin": {"x": 0.5, "y": 64, "z": 0.5},
                    "candidates": candidates
                    if candidates is not None
                    else [{"x": -8, "y": 64, "z": 0}],
                }
            },
            "position": observation.position.model_copy(update={"x": 0, "y": 64, "z": 0}),
        }
    )


def available():
    return ExecutionBudget(
        queue_timeout_ms=1000,
        execution_timeout_ms=10000,
        max_actions=16,
        max_strategy_attempts=4,
        max_travel_distance=64,
        max_blocks_changed=64,
        max_damage_taken=0,
    )


def manifest():
    value = RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    goto = value.capabilities[0].model_copy(update={"name": "goto"})
    return value.model_copy(update={"capabilities": (*value.capabilities, goto)})


def test_retreat_is_charged_in_original_account_and_does_not_advance_material_workflow():
    registry = WorkflowRegistry()
    registry.register(iron_survival_workflow())
    strategy = MissionStrategy(
        manifest=manifest(),
        builtin=None,
        live=None,
        learn=None,
        fallback=FallbackStrategy(registry=registry),
    )
    goal = TypeAdapter(GoalSpec).validate_python(
        {
            "intent": "acquire",
            "target": "iron_ingot",
            "quantity": 1,
            "success_predicates": [
                {"kind": "inventory_at_least", "item": "iron_ingot", "quantity": 1}
            ],
        }
    )
    state = strategy.prepare(goal)
    state["budget_remaining"] = available()
    decision = strategy.propose(state, observed())
    assert decision.capability == "goto"
    assert decision.parameters == {"x": -8, "y": 64, "z": 0}
    assert decision.maximum_cost.max_actions == 1
    assert decision.maximum_cost.max_travel_distance == 64
    assert decision.maximum_cost.max_blocks_changed == 0
    assert decision.maximum_cost.max_damage_taken == 0
    state = strategy.accept_result(state, {"outcome": "success"})
    assert state["goal"] == goal
    assert state["strategy_state"]["step_index"] == 0
    assert state["executed_steps"] == 0
    state["budget_remaining"] = available().model_copy(
        update={"max_actions": 15, "max_travel_distance": 56}
    )
    next_decision = strategy.propose(state, observed())
    assert next_decision.capability == "collect"
    assert next_decision.parameters == {"block_type": "any_log", "count": 8}
    assert state["retreat_destinations"] == ((-8, 64, 0),)


def test_retreat_rejects_unknown_evidence_and_preserves_two_block_stopping_reserve():
    state = {"budget_remaining": available().model_copy(update={"max_travel_distance": 9})}
    assert propose_retreat(state, observed()) is None
    state["budget_remaining"] = available().model_copy(update={"max_travel_distance": 10})
    assert propose_retreat(state, observed()) is None
    state["budget_remaining"] = available().model_copy(update={"max_travel_distance": 11})
    assert propose_retreat(state, observed()) is not None
    state["budget_remaining"] = available().model_copy(update={"max_actions": 0})
    assert propose_retreat(state, observed()) is None
    state["budget_remaining"] = available()
    for invalid in [
        [],
        [{"x": float("nan"), "y": 64, "z": 0}],
        [{"x": True, "y": 64, "z": 0}],
        [{"x": 1.5, "y": 64, "z": 0}],
    ]:
        assert propose_retreat(state, observed(invalid)) is None


def test_completed_mission_primitive_does_not_start_an_unnecessary_retreat():
    class Done:
        def prepare(self, goal):
            return {}

        def propose(self, state, observation):
            return Complete()

    strategy = MissionStrategy(
        manifest=manifest(),
        builtin=Done(),
        live=None,
        learn=None,
        fallback=None,
    )
    goal = TypeAdapter(GoalSpec).validate_python(
        {
            "intent": "acquire",
            "target": "iron_ingot",
            "quantity": 1,
            "success_predicates": [
                {"kind": "inventory_at_least", "item": "iron_ingot", "quantity": 1}
            ],
        }
    )
    state = strategy.prepare(goal)
    state["budget_remaining"] = available()
    assert isinstance(strategy.propose(state, observed()), Complete)
