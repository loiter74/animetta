"""Reactive retreat uses the original mission account and preserves its workflow."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.survival.recovery import propose_recovery_move
from animetta.tools.minecraft.survival.registry import WorkflowRegistry
from animetta.tools.minecraft.survival.retreat import propose_retreat
from animetta.tools.minecraft.survival.workflows import iron_survival_workflow
from animetta.tools.minecraft.voyager.budget import BudgetUsage, ExecutionBudget
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


def test_known_failure_replans_from_fresh_evidence_without_advancing_the_workflow():
    registry = WorkflowRegistry()
    registry.register(iron_survival_workflow())
    strategy = MissionStrategy(
        manifest=manifest(),
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
    before = observed([])
    failed_collect = strategy.propose(state, before)
    assert failed_collect.capability == "collect"
    assert strategy.recover_failed_step(state, failed_collect, before, before) is None
    assert "pending_retreat" not in state
    recovered = strategy.recover_failed_step(state, failed_collect, before, observed())
    assert recovered is not None
    assert recovered["goal"] == goal
    assert recovered["selected_strategy"] == state["selected_strategy"] == "fallback"
    assert recovered["strategy_state"]["step_index"] == state["strategy_state"]["step_index"] == 0
    assert recovered["executed_steps"] == 0
    assert "pending_retreat" not in state
    retreat = strategy.propose(recovered, observed())
    assert retreat.capability == "goto"
    resumed = strategy.accept_result(recovered, {"outcome": "success"})
    assert strategy.propose(resumed, observed([])) == failed_collect


def test_failed_retreat_is_not_replayed_or_counted_as_workflow_success():
    registry = WorkflowRegistry()
    registry.register(iron_survival_workflow())
    strategy = MissionStrategy(
        manifest=manifest(),
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
    failed_retreat = strategy.propose(state, observed())
    recovered = strategy.recover_failed_step(state, failed_retreat, observed(), observed())
    assert recovered is not None
    assert recovered["retreat_destinations"] == ((-8, 64, 0),)
    assert state["pending_retreat"] == (-8, 64, 0)
    assert recovered["strategy_state"]["step_index"] == 0
    assert recovered["executed_steps"] == 0
    assert strategy.propose(recovered, observed()).capability == "collect"


@pytest.mark.parametrize("code", ["RESOURCE_NOT_FOUND", "SEARCH_TIMEOUT"])
def test_resource_search_can_continue_at_a_new_observed_origin_but_never_replays_a_scene(code):
    registry = WorkflowRegistry()
    registry.register(iron_survival_workflow())
    strategy = MissionStrategy(
        manifest=manifest(), live=None, learn=None, fallback=FallbackStrategy(registry=registry)
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
    state.update(budget_remaining=available(), settled_error_code=code)

    def sample(x, y, z):
        base = observed([])
        return base.model_copy(
            update={
                "position": base.position.model_copy(update={"x": x, "y": y, "z": z}),
                "environment": {
                    "blocks": {
                        "feet": {"name": "air", "position": {"x": x, "y": y, "z": z}},
                        "below1": {"name": "sand", "position": {"x": x, "y": y - 1, "z": z}},
                    }
                },
            }
        )

    # R76's settled rounded positions; this is a pure control-plane replay,
    # not a claim about whether the original world contained reachable wood.
    before, after = sample(73, 65, 44), sample(68, 64, 47)
    failed = strategy.propose(state, before)
    assert failed.capability == "collect"
    assert strategy.recover_failed_step(state, failed, before, before) is None
    changed_count = failed.model_copy(
        update={"parameters": {**failed.parameters, "count": failed.parameters["count"] - 1}}
    )
    assert strategy.recover_failed_step(state, changed_count, before, before) is None
    assert (
        strategy.recover_failed_step(
            state, failed, before, after.model_copy(update={"environment": before.environment})
        )
        is None
    )
    recovered = strategy.recover_failed_step(state, failed, before, after)
    assert recovered is not None
    assert recovered["goal"] == goal
    assert recovered["strategy_state"]["step_index"] == state["strategy_state"]["step_index"] == 0
    assert recovered["executed_steps"] == 0
    assert strategy.propose(recovered, after) == failed
    assert strategy.recover_failed_step(recovered, failed, after, before) is None
    assert (
        strategy.recover_failed_step(
            {**state, "settled_error_code": "UNSAFE_AREA"}, failed, before, after
        )
        is None
    )
    assert "search_origins" not in state


@pytest.mark.parametrize("code", ["RESOURCE_NOT_FOUND", "SEARCH_TIMEOUT"])
def test_stationary_search_continues_only_with_receipt_linked_known_block_progress(code):
    registry = WorkflowRegistry()
    registry.register(iron_survival_workflow())
    strategy = MissionStrategy(
        manifest=manifest(), live=None, learn=None, fallback=FallbackStrategy(registry=registry)
    )
    goal = TypeAdapter(GoalSpec).validate_python(
        {
            "intent": "acquire",
            "target": "iron_ingot",
            "quantity": 3,
            "success_predicates": [
                {"kind": "inventory_at_least", "item": "iron_ingot", "quantity": 3}
            ],
        }
    )
    state = strategy.prepare(goal)
    state.update(budget_remaining=available(), settled_error_code=code)

    def sample(west="stone", ceiling="stone"):
        base = observed([])
        return base.model_copy(
            update={
                "position": base.position.model_copy(update={"x": 26, "y": 111, "z": 18}),
                "inventory": {"stone_pickaxe": 1, "raw_iron": 1},
                "environment": {
                    "dimension": "overworld",
                    "blocks": {
                        "west_support": {"name": west, "position": {"x": 24, "y": 110, "z": 18}},
                        "ceiling": {"name": ceiling, "position": {"x": 25, "y": 113, "z": 18}},
                    },
                },
            }
        )

    # R81's stationary search removed this observed support-side stone. No
    # receipt-linked change, unknown old cell, or clock-only change can retry.
    before, after = sample(), sample("air")
    failed = strategy.propose(state, before)
    assert failed.capability == "collect" and failed.parameters["block_type"] == "iron_ore"
    index = state["strategy_state"]["step_index"]
    assert strategy.recover_failed_step(state, failed, before, after) is None
    subject = "block:minecraft:overworld:24:110:18"
    linked = {**state, "settled_block_subjects": (subject,)}
    assert strategy.recover_failed_step(linked, failed, before, before) is None
    assert (
        strategy.recover_failed_step(
            {**linked, "settled_block_subjects": ("block:minecraft:the_nether:24:110:18",)},
            failed,
            before,
            after,
        )
        is None
    )
    unknown = before.model_copy(update={"environment": {"dimension": "overworld", "blocks": {}}})
    assert strategy.recover_failed_step(linked, failed, unknown, after) is None
    recovered = strategy.recover_failed_step(linked, failed, before, after)
    assert recovered is not None
    assert recovered["goal"] == goal and recovered["executed_steps"] == 0
    assert recovered["strategy_state"]["step_index"] == index
    assert strategy.propose(recovered, after) == failed
    assert strategy.recover_failed_step(recovered, failed, after, before) is None
    more = {**recovered, "settled_block_subjects": ("block:minecraft:overworld:25:113:18",)}
    assert strategy.recover_failed_step(more, failed, after, sample("air", "air")) is not None
    assert (
        strategy.recover_failed_step(
            {**linked, "settled_error_code": "UNSAFE_AREA"},
            failed,
            before,
            after,
        )
        is None
    )


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


def recovery_observation():
    base = observed([])
    return base.model_copy(
        update={
            "environment": {
                "dimension": "overworld",
                "blocks": {
                    "feet": {"name": "air", "position": {"x": 0, "y": 64, "z": 0}},
                    "head": {"name": "air", "position": {"x": 0, "y": 65, "z": 0}},
                },
            }
        }
    )


def recovery_strategy():
    native = manifest()
    explorer = native.capability("goto").model_copy(
        update={
            "name": "explore_surface",
            "parameters_schema": {
                "type": "object",
                "properties": {axis: {"type": "integer"} for axis in ("x", "z")},
                "additionalProperties": False,
            },
            "maximum_cost": native.capability("goto").maximum_cost.model_copy(
                update={
                    "max_strategy_attempts": 0,
                    "max_travel_distance": 0.0,
                    "max_blocks_changed": 0,
                    "max_damage_taken": 0.0,
                }
            ),
        }
    )
    native = native.model_copy(update={"capabilities": (*native.capabilities, explorer)})
    registry = WorkflowRegistry()
    registry.register(iron_survival_workflow())
    strategy = MissionStrategy(
        manifest=native, live=None, learn=None, fallback=FallbackStrategy(registry=registry)
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
    state["settled_error_code"] = "SEARCH_TIMEOUT"
    state["settled_feedback"] = {"receipt_hash": "a" * 64}
    return strategy, state


def test_sparse_search_failure_explores_without_skipping_work_or_replenishing_budget():
    from animetta.tools.minecraft.voyager.budget import BudgetAccount

    strategy, state = recovery_strategy()
    observation = recovery_observation()
    failed = strategy.propose(state, observation)
    assert failed.capability == "collect"
    account = BudgetAccount(limit=available()).charge(
        BudgetUsage(max_actions=1, max_travel_distance=2)
    )
    state["budget_remaining"] = account.remaining
    recovered = strategy.recover_failed_step(state, failed, observation, observation)
    assert recovered is not None
    move = strategy.propose(recovered, observation)
    assert move.capability == "explore_surface" and move.parameters == {"x": 8, "z": 0}
    assert move.maximum_cost.max_travel_distance == 16
    assert recovered["strategy_state"]["step_index"] == 0
    assert recovered["recovery_decisions"][0]["receipt_hash"] == "a" * 64
    assert "pending_recovery_move" not in state
    account = account.charge(BudgetUsage(max_actions=1, max_travel_distance=8))
    resumed = strategy.accept_result(recovered, {"outcome": "success"})
    after = observation.model_copy(
        update={"position": observation.position.model_copy(update={"x": 8})}
    )
    resumed["budget_remaining"] = account.remaining
    assert strategy.propose(resumed, after).capability == "collect"
    assert resumed["strategy_state"]["step_index"] == 0
    assert account.limit == available()
    assert account.remaining.max_actions == 14 and account.remaining.max_travel_distance == 54


def test_zero_progress_exploration_never_replays_the_failed_collection_or_column():
    from animetta.tools.minecraft.voyager.budget import BudgetAccount
    from animetta.tools.minecraft.voyager.strategies.base import StrategyFailure

    strategy, state = recovery_strategy()
    observation = recovery_observation()
    failed = strategy.propose(state, observation)
    account = BudgetAccount(limit=available()).charge(BudgetUsage(max_actions=1))
    state["budget_remaining"] = account.remaining
    state = strategy.recover_failed_step(state, failed, observation, observation)
    columns = []
    for _ in range(8):
        move = strategy.propose(state, observation)
        assert move.capability == "explore_surface"
        columns.append(tuple(move.parameters[axis] for axis in ("x", "z")))
        account = account.charge(BudgetUsage(max_actions=1))
        state = strategy.accept_result(state, {"outcome": "success"})
        state["budget_remaining"] = account.remaining
    assert len(set(columns)) == 8
    assert isinstance(strategy.propose(state, observation), StrategyFailure)
    assert state["strategy_state"]["step_index"] == 0
    assert account.used.max_actions == 9


def test_failed_recovery_exploration_changes_column_and_partial_progress_keeps_workflow():
    strategy, state = recovery_strategy()
    observation = recovery_observation()
    failed = strategy.propose(state, observation)
    state = strategy.recover_failed_step(state, failed, observation, observation)
    move = strategy.propose(state, observation)
    state["settled_error_code"] = "NAVIGATION_TARGET_NOT_REACHED"
    second = strategy.recover_failed_step(state, move, observation, observation)
    assert second is not None
    assert strategy.propose(second, observation).parameters == {"x": 8, "z": 8}
    after = observation.model_copy(
        update={"position": observation.position.model_copy(update={"x": 2})}
    )
    progressed = strategy.accept_partial_result(
        {**state, "settled_capability": "explore_surface"}, observation, after
    )
    assert progressed is not None and progressed["strategy_state"]["step_index"] == 0
    assert strategy.propose(progressed, after).capability == "collect"
    assert (
        strategy.accept_partial_result(
            {**state, "settled_capability": "collect"}, observation, after
        )
        is None
    )


@pytest.mark.parametrize(
    "change", [{"max_actions": 1}, {"max_travel_distance": 8.0}, {"max_actions": 0}]
)
def test_recovery_exploration_keeps_action_and_travel_reserves(change):
    assert (
        propose_recovery_move(
            recovery_observation(),
            remaining=available().model_copy(update=change),
            minimum_cost=BudgetUsage(max_actions=1),
            anchor=(0, 64, 0),
            attempted=(),
        )
        is None
    )


def test_recovery_does_not_handle_unknown_failure_or_cross_dimension():
    strategy, state = recovery_strategy()
    observation = recovery_observation()
    failed = strategy.propose(state, observation)
    state["settled_error_code"] = "RUNTIME_DISCONNECTED"
    assert strategy.recover_failed_step(state, failed, observation, observation) is None
    state["settled_error_code"] = "SEARCH_TIMEOUT"
    changed = observation.model_copy(
        update={"environment": {**observation.environment, "dimension": "the_nether"}}
    )
    assert strategy.recover_failed_step(state, failed, observation, changed) is None
    state = strategy.recover_failed_step(state, failed, observation, observation)
    move = strategy.propose(state, observation)
    assert strategy.recover_failed_step(state, move, observation, changed) is None
