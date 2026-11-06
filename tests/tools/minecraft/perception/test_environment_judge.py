"""Deterministic rule judge over authoritative GameBot observations."""

from __future__ import annotations

import json
from pathlib import Path

from animetta.tools.gamebot.contracts.v2 import DiscoverableEntity, Observation, Position
from animetta.tools.gamebot.contracts.v2.observations import DiscoverableBlock
from animetta.tools.minecraft.perception.environment import EnvironmentJudge
from animetta.tools.minecraft.perception.models import PerceptionDanger

ROOT = Path(__file__).resolve().parents[4]
MESSAGES = json.loads(
    (ROOT / "contracts/gamebot/v2/fixtures/golden.json").read_text(encoding="utf-8")
)["messages"]


def _observation(**overrides: object) -> Observation:
    return Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={
            "position": Position(x=0.0, y=64.0, z=0.0),
            "health": 20.0,
            "food": 20,
            "visible_entities": (),
            "visible_blocks": (),
            **overrides,
        }
    )


def _entity(entity_type: str, *, x: float, z: float, y: float = 64.0) -> DiscoverableEntity:
    return DiscoverableEntity(
        entity_id="entity-1",
        entity_type=entity_type,
        position=Position(x=x, y=y, z=z),
        health=10.0,
    )


def _block(block_id: str, *, x: float, z: float, y: float = 64.0) -> DiscoverableBlock:
    return DiscoverableBlock(block_id=block_id, position=Position(x=x, y=y, z=z))


class TestEnvironmentJudgeSafety:
    def test_safe_observation_reports_no_danger(self) -> None:
        verdict = EnvironmentJudge().assess(_observation())

        assert verdict.available is True
        assert verdict.danger is PerceptionDanger.NONE
        assert verdict.threats == ()
        assert verdict.health_critical is False
        assert verdict.food_critical is False
        assert verdict.stuck is False

    def test_close_hostile_entity_is_critical(self) -> None:
        observation = _observation(visible_entities=(_entity("minecraft:zombie", x=3.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.CRITICAL
        assert verdict.nearest_hostile_blocks == 3.0
        assert verdict.threats == ("zombie:3.0m",)
        assert verdict.details["nearest_hostile_blocks"] == 3.0

    def test_hostile_beyond_critical_but_within_warning(self) -> None:
        observation = _observation(visible_entities=(_entity("minecraft:zombie", x=6.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.WARNING
        assert verdict.nearest_hostile_blocks == 6.0

    def test_distant_hostile_entity_is_safe(self) -> None:
        observation = _observation(visible_entities=(_entity("minecraft:skeleton", x=20.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.NONE

    def test_creeper_uses_larger_critical_radius(self) -> None:
        observation = _observation(visible_entities=(_entity("minecraft:creeper", x=5.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.CRITICAL

    def test_passive_entities_are_ignored(self) -> None:
        observation = _observation(visible_entities=(_entity("minecraft:cow", x=1.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.NONE
        assert verdict.nearest_hostile_blocks is None


class TestEnvironmentJudgeVitals:
    def test_critical_health_is_critical(self) -> None:
        verdict = EnvironmentJudge().assess(_observation(health=5.0))

        assert verdict.danger is PerceptionDanger.CRITICAL
        assert verdict.health_critical is True
        assert "health:5.0" in verdict.threats

    def test_low_health_is_warning(self) -> None:
        verdict = EnvironmentJudge().assess(_observation(health=10.0))

        assert verdict.danger is PerceptionDanger.WARNING
        assert verdict.health_critical is False
        assert "health_low:10.0" in verdict.threats

    def test_starving_food_is_warning(self) -> None:
        verdict = EnvironmentJudge().assess(_observation(food=1))

        assert verdict.danger is PerceptionDanger.WARNING
        assert verdict.food_critical is True
        assert "food:1" in verdict.threats


class TestEnvironmentJudgeHazards:
    def test_adjacent_lava_is_critical(self) -> None:
        observation = _observation(visible_blocks=(_block("minecraft:lava", x=1.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.CRITICAL
        assert verdict.threats == ("lava:1.0m",)

    def test_nearby_cactus_is_warning(self) -> None:
        observation = _observation(visible_blocks=(_block("minecraft:cactus", x=1.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.WARNING
        assert verdict.threats == ("cactus:1.0m",)

    def test_far_hazard_is_safe(self) -> None:
        observation = _observation(visible_blocks=(_block("minecraft:lava", x=12.0, z=0.0),))

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.NONE


class TestEnvironmentJudgeStuck:
    def test_stationary_history_is_stuck(self) -> None:
        history = tuple(_observation() for _ in range(4))

        verdict = EnvironmentJudge().assess(_observation(), history)

        assert verdict.stuck is True
        assert verdict.danger is PerceptionDanger.WARNING
        assert "position_stuck" in verdict.threats

    def test_short_history_is_not_stuck(self) -> None:
        history = tuple(_observation() for _ in range(2))

        verdict = EnvironmentJudge().assess(_observation(), history)

        assert verdict.stuck is False

    def test_moving_history_is_not_stuck(self) -> None:
        history = tuple(
            _observation(position=Position(x=float(index) * 4.0, y=64.0, z=0.0))
            for index in range(4)
        )

        verdict = EnvironmentJudge().assess(_observation(), history)

        assert verdict.stuck is False


class TestEnvironmentJudgeEscalation:
    def test_danger_escalates_to_strongest_signal(self) -> None:
        observation = _observation(
            health=5.0,
            visible_entities=(_entity("minecraft:zombie", x=6.0, z=0.0),),
        )

        verdict = EnvironmentJudge().assess(observation)

        assert verdict.danger is PerceptionDanger.CRITICAL
        assert "health:5.0" in verdict.threats
        assert "zombie:6.0m" in verdict.threats
