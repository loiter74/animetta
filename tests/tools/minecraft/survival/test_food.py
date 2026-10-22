"""Recovery decisions depend on observed food and independently observed health."""

import json
from pathlib import Path

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.survival.food import build_food_recovery_mission
from animetta.tools.minecraft.voyager.goal_models import FoodAtLeast, HealthAtLeast
from animetta.tools.minecraft.voyager.strategies.builtin import BuiltinMissionStrategy

MESSAGES = json.loads(
    (Path(__file__).resolve().parents[4] / "contracts/gamebot/v2/fixtures/golden.json").read_text(
        encoding="utf-8"
    )
)["messages"]


def test_food_recovery_eats_waits_then_requires_real_health() -> None:
    mission = build_food_recovery_mission(mission_id="food-test")
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "health": 3.3,
            "food": 17,
            "inventory": {"minecraft:apple": 1},
        }
    )
    decision = strategy.propose(state, observation)
    assert decision.kind == "execute" and decision.capability == "eat"
    assert decision.parameters == {"item": "apple"}
    state = strategy.accept_result(state, {})
    fed = observation.model_copy(update={"inventory": {}, "food": 20})
    waiting = strategy.propose(state, fed)
    assert waiting.kind == "execute" and waiting.capability == "wait_for_regeneration"
    assert strategy.propose(state, fed.model_copy(update={"health": 8})).kind == "complete"


def test_food_recovery_obeys_finite_step_limit() -> None:
    mission = build_food_recovery_mission(mission_id="food-test")
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    state["completed_steps"] = 96
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"health": 3.3}
    )
    decision = strategy.propose(state, observation)
    assert decision.kind == "failure" and decision.code == "RECOVERY_BUDGET_EXHAUSTED"


def test_food_recovery_explores_surface_without_fixed_y() -> None:
    mission = build_food_recovery_mission(mission_id="food-test")
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "health": 3.3,
            "food": 15,
            "inventory": {},
            "position": {"x": 12.0, "y": 61.0, "z": -5.0},
            "visible_entities": [],
            "visible_blocks": [],
        }
    )
    decision = strategy.propose(state, observation)
    assert decision.kind == "execute" and decision.capability == "explore_surface"
    # Surface exploration stays on the horizontal plane: no pinned y coordinate
    # may steer the bot toward an underground height while health < 8.
    assert set(decision.parameters) == {"x", "z"}
    assert "y" not in decision.parameters


def test_food_recovery_abandons_stalled_leaves_for_surface_exploration() -> None:
    mission = build_food_recovery_mission(mission_id="food-test")
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(
        {
            **MESSAGES["Observation"],
            "health": 3.3,
            "food": 15,
            "inventory": {},
            "position": {"x": 12.0, "y": 61.0, "z": -5.0},
            "visible_entities": [],
            "visible_blocks": [
                {
                    "block_id": "minecraft:oak_leaves",
                    "position": {"x": 5.0, "y": 68.0, "z": 7.0},
                }
            ],
        }
    )
    decisions = []
    for _ in range(3):
        decision = strategy.propose(state, observation)
        assert decision.kind != "complete"
        decisions.append(decision)
        state = strategy.accept_result(state, {})
    assert decisions[0].capability == "forage_apples"
    assert decisions[-1].kind == "execute" and decisions[-1].capability == "explore_surface"
    assert [step.capability for step in decisions].count("forage_apples") <= 2


def test_food_recovery_mission_keeps_health_only_predicates_by_default() -> None:
    mission = build_food_recovery_mission(mission_id="food-test")

    predicates = mission.objectives[0].goal.success_predicates

    assert [predicate.kind for predicate in predicates] == ["health_at_least"]
    assert all(not isinstance(predicate, FoodAtLeast) for predicate in predicates)


def test_food_recovery_mission_with_food_declares_health_and_food_predicates() -> None:
    mission = build_food_recovery_mission(mission_id="food-test", food=18)

    predicates = mission.objectives[0].goal.success_predicates

    assert [predicate.kind for predicate in predicates] == [
        "health_at_least",
        "food_at_least",
    ]
    assert isinstance(predicates[0], HealthAtLeast) and predicates[0].health == 8
    assert isinstance(predicates[1], FoodAtLeast) and predicates[1].food == 18


def test_food_recovery_full_health_with_low_food_keeps_eating() -> None:
    mission = build_food_recovery_mission(mission_id="food-test", food=18)
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"health": 20.0, "food": 12, "inventory": {"minecraft:apple": 2}}
    )

    decision = strategy.propose(state, observation)

    assert decision.kind == "execute" and decision.capability == "eat"
    assert decision.parameters == {"item": "apple"}


def test_food_recovery_completes_when_health_and_declared_food_satisfied() -> None:
    mission = build_food_recovery_mission(mission_id="food-test", food=18)
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"health": 20.0, "food": 18, "inventory": {}}
    )

    decision = strategy.propose(state, observation)

    assert decision.kind == "complete"


def test_food_recovery_unknown_food_fails_instead_of_completing() -> None:
    mission = build_food_recovery_mission(mission_id="food-test", food=18)
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"health": 20.0, "food": None}
    )

    decision = strategy.propose(state, observation)

    assert decision.kind == "failure" and decision.code == "RECOVERY_STATE_UNKNOWN"


def test_food_recovery_waits_for_regeneration_only_when_food_condition_satisfied() -> None:
    mission = build_food_recovery_mission(mission_id="food-test", food=18)
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"health": 3.3, "food": 18, "inventory": {}}
    )

    decision = strategy.propose(state, observation)

    assert decision.kind == "execute" and decision.capability == "wait_for_regeneration"


def test_food_recovery_food_threshold_above_regeneration_floor_must_eat() -> None:
    mission = build_food_recovery_mission(mission_id="food-test", food=20)
    strategy = BuiltinMissionStrategy(
        manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    )
    state = strategy.prepare(mission.objectives[0].goal)
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"health": 8.0, "food": 18, "inventory": {"minecraft:apple": 1}}
    )

    decision = strategy.propose(state, observation)

    # Food 18 cannot rise by waiting: regeneration never feeds the hunger bar,
    # so a threshold above 18 must keep eating instead of deadlooping on waits.
    assert decision.kind == "execute" and decision.capability == "eat"
