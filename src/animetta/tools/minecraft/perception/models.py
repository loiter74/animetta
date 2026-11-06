"""Typed verdict and consensus contracts for dual-perception safety checks."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _PerceptionModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PerceptionDanger(StrEnum):
    """Safety-first ordering: the highest reported danger always wins."""

    NONE = "none"
    WARNING = "warning"
    CRITICAL = "critical"

    def at_least(self, other: PerceptionDanger) -> PerceptionDanger:
        """Return the more severe of the two dangers (NOT string order)."""

        order = {
            PerceptionDanger.NONE: 0,
            PerceptionDanger.WARNING: 1,
            PerceptionDanger.CRITICAL: 2,
        }
        return self if order[self] >= order[other] else other


class VisionVerdict(_PerceptionModel):
    """Judgement from the local vision model over one spectator frame."""

    available: bool = True
    danger: PerceptionDanger = PerceptionDanger.NONE
    scene_summary: str = Field(default="", max_length=280)
    threats: tuple[str, ...] = Field(default=(), max_length=8)
    goal_plausible: bool | None = Field(default=None)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    model: str = Field(default="", max_length=128)
    error: str | None = Field(default=None, max_length=280)


class EnvironmentVerdict(_PerceptionModel):
    """Deterministic structural analysis of the authoritative observation."""

    available: bool = True
    danger: PerceptionDanger = PerceptionDanger.NONE
    threats: tuple[str, ...] = Field(default=(), max_length=8)
    health_critical: bool = False
    food_critical: bool = False
    nearest_hostile_blocks: float | None = Field(default=None, ge=0.0)
    stuck: bool = False
    details: dict[str, object] = Field(default_factory=dict)


class PerceptionConsensus(_PerceptionModel):
    """Safety-first merged verdict of both perception agents."""

    adopted_danger: PerceptionDanger = PerceptionDanger.NONE
    vision: VisionVerdict = Field(default_factory=VisionVerdict)
    environment: EnvironmentVerdict = Field(default_factory=EnvironmentVerdict)
    agreement: bool = False
    action: Literal["continue", "alert", "halt"] = "continue"
    headline: str = Field(default="感知检查完成", min_length=1, max_length=64)
    reason: str = Field(default="", max_length=280)
    checked_at_ms: int = Field(default=0, ge=0)
    mode: Literal["monitor", "verify_completion"] = "monitor"
