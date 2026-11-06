"""Deterministic environment judge over authoritative GameBot observations.

This judge is intentionally LLM-free: it reads only the structured
``Observation`` contract, so its numeric verdicts stay reproducible and cheap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from animetta.tools.gamebot.contracts.v2.observations import Observation, Position

from .models import EnvironmentVerdict, PerceptionDanger

_HOSTILE_ENTITY_TYPES = frozenset(
    {
        "zombie",
        "skeleton",
        "creeper",
        "spider",
        "cave_spider",
        "witch",
        "blaze",
        "ghast",
        "enderman",
        "slime",
        "magma_cube",
        "drowned",
        "husk",
        "stray",
        "phantom",
        "pillager",
        "vindicator",
        "ravager",
        "vex",
        "evoker",
        "warden",
        "wither_skeleton",
        "piglin_brute",
        "hoglin",
        "zoglin",
        "breeze",
        "bogged",
        "creaking",
    }
)
_INSTANT_HAZARD_BLOCKS = frozenset({"lava", "fire", "soul_fire", "magma_block"})
_PROXIMITY_HAZARD_BLOCKS = frozenset(
    {"campfire", "cactus", "pointed_dripstone", "sweet_berry_bush"}
)


def _short_id(identifier: str) -> str:
    return identifier.removeprefix("minecraft:").removeprefix("entity.minecraft:")


def _distance(a: Position, b: Position) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


@dataclass(frozen=True, slots=True)
class EnvironmentThresholds:
    """Numeric guard rails mirrored from ``MinecraftPerceptionConfig``."""

    health_critical: float = 6.0
    health_warning: float = 12.0
    food_critical: int = 2
    hostile_warning_blocks: float = 8.0
    hostile_critical_blocks: float = 3.5
    creeper_critical_blocks: float = 6.0
    hazard_warning_blocks: float = 6.0
    hazard_critical_blocks: float = 3.0
    stuck_radius: float = 1.5
    stuck_minimum_samples: int = 4


class EnvironmentJudge:
    """Pure rule judge: observation history in, typed environment verdict out."""

    def __init__(self, thresholds: EnvironmentThresholds | None = None) -> None:
        self._thresholds = thresholds or EnvironmentThresholds()

    def assess(
        self,
        observation: Observation,
        history: tuple[Observation, ...] = (),
    ) -> EnvironmentVerdict:
        thresholds = self._thresholds
        danger = PerceptionDanger.NONE
        threats: list[str] = []
        details: dict[str, object] = {}

        health = observation.health
        if health is not None:
            if health <= thresholds.health_critical:
                danger = danger.at_least(PerceptionDanger.CRITICAL)
                threats.append(f"health:{health:.1f}")
            elif health <= thresholds.health_warning:
                danger = danger.at_least(PerceptionDanger.WARNING)
                threats.append(f"health_low:{health:.1f}")
        food = observation.food
        food_critical = food is not None and food <= thresholds.food_critical
        if food_critical:
            danger = danger.at_least(PerceptionDanger.WARNING)
            threats.append(f"food:{food}")

        position = observation.position
        nearest_hostile: float | None = None
        nearest_hostile_name: str | None = None
        if position is not None:
            for entity in observation.visible_entities:
                entity_type = _short_id(entity.entity_type)
                if entity_type not in _HOSTILE_ENTITY_TYPES:
                    continue
                distance = _distance(position, entity.position)
                if nearest_hostile is None or distance < nearest_hostile:
                    nearest_hostile = distance
                    nearest_hostile_name = entity_type
                critical_range = (
                    thresholds.creeper_critical_blocks
                    if entity_type == "creeper"
                    else thresholds.hostile_critical_blocks
                )
                if distance < critical_range:
                    danger = danger.at_least(PerceptionDanger.CRITICAL)
                elif distance < thresholds.hostile_warning_blocks:
                    danger = danger.at_least(PerceptionDanger.WARNING)
            if nearest_hostile_name is not None and nearest_hostile is not None:
                threats.append(f"{nearest_hostile_name}:{nearest_hostile:.1f}m")

            hazard_nearest: float | None = None
            hazard_name: str | None = None
            for block in observation.visible_blocks:
                block_type = _short_id(block.block_id)
                instant = block_type in _INSTANT_HAZARD_BLOCKS
                if not instant and block_type not in _PROXIMITY_HAZARD_BLOCKS:
                    continue
                distance = _distance(position, block.position)
                if hazard_nearest is None or distance < hazard_nearest:
                    hazard_nearest = distance
                    hazard_name = block_type
                if instant and distance < thresholds.hazard_critical_blocks:
                    danger = danger.at_least(PerceptionDanger.CRITICAL)
                elif distance < thresholds.hazard_warning_blocks:
                    danger = danger.at_least(PerceptionDanger.WARNING)
            if hazard_name is not None and hazard_nearest is not None:
                threats.append(f"{hazard_name}:{hazard_nearest:.1f}m")

        stuck = self._is_stuck(observation, history)
        if stuck:
            danger = danger.at_least(PerceptionDanger.WARNING)
            threats.append("position_stuck")

        if nearest_hostile is not None:
            details["nearest_hostile_blocks"] = round(nearest_hostile, 2)
        if health is not None:
            details["health"] = health
        if food is not None:
            details["food"] = food
        if position is not None:
            details["position"] = [position.x, position.y, position.z]

        return EnvironmentVerdict(
            danger=danger,
            threats=tuple(threats[:8]),
            health_critical=health is not None and health <= thresholds.health_critical,
            food_critical=food_critical,
            nearest_hostile_blocks=round(nearest_hostile, 2)
            if nearest_hostile is not None
            else None,
            stuck=stuck,
            details=details,
        )

    def _is_stuck(self, observation: Observation, history: tuple[Observation, ...]) -> bool:
        position = observation.position
        if position is None:
            return False
        thresholds = self._thresholds
        samples = [item for item in history if item.position is not None]
        if len(samples) < thresholds.stuck_minimum_samples:
            return False
        recent = samples[-thresholds.stuck_minimum_samples :]
        return all(_distance(position, item.position) <= thresholds.stuck_radius for item in recent)
