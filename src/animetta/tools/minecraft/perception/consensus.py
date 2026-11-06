"""Safety-first arbiter merging vision and environment verdicts."""

from __future__ import annotations

import re
from typing import Literal

from .models import (
    EnvironmentVerdict,
    PerceptionConsensus,
    PerceptionDanger,
    VisionVerdict,
)

_UNSAFE_TEXT = re.compile(r"(?i)(?:\bBearer\s+|\bsk-[A-Za-z0-9_-]{6,}|[\r\n\x00-\x1f])")
_DANGER_LABEL = {
    PerceptionDanger.NONE: "安全",
    PerceptionDanger.WARNING: "告警",
    PerceptionDanger.CRITICAL: "危险",
}


def _sanitize(value: str) -> str:
    cleaned = _UNSAFE_TEXT.sub(" ", value).strip()
    return cleaned.replace("  ", " ")


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _threat_headline(threats: tuple[str, ...], limit: int) -> str:
    joined = "；".join(_sanitize(item) for item in threats[:3] if item)
    return _truncate(joined, limit)


def combine(
    *,
    vision: VisionVerdict,
    environment: EnvironmentVerdict,
    checked_at_ms: int,
    mode: Literal["monitor", "verify_completion"] = "monitor",
) -> PerceptionConsensus:
    """Merge both agents with safety-first semantics.

    - The highest danger reported by either agent is always adopted.
    - A critical verdict from any single agent triggers ``halt``.
    - An unavailable vision agent never masks environment danger and vice
      versa; ``agreement`` stays ``False`` in degraded runs.
    """

    adopted = vision.danger.at_least(environment.danger) if vision.available else environment.danger
    if not environment.available and vision.available:
        adopted = vision.danger
    both_available = vision.available and environment.available
    agreement = both_available and vision.danger is environment.danger

    action: Literal["continue", "alert", "halt"] = "continue"
    if adopted is PerceptionDanger.CRITICAL:
        action = "halt"
    elif adopted is PerceptionDanger.WARNING:
        action = "alert"

    source = "双感知一致" if agreement else "安全优先仲裁"
    if not vision.available:
        source = "环境单感知(视觉不可用)"
    elif not environment.available:
        source = "视觉单感知(环境不可用)"

    threats: tuple[str, ...] = ()
    if adopted is not PerceptionDanger.NONE:
        merged: list[str] = []
        for item in (*environment.threats, *vision.threats):
            label = _sanitize(item)
            if label and label not in merged:
                merged.append(label)
        threats = tuple(merged[:4])

    headline = f"{source}:{_DANGER_LABEL[adopted]}"
    detail = _threat_headline(threats, 64 - len(headline) - 1)
    if detail:
        headline = f"{headline}-{detail}"
    if mode == "verify_completion" and vision.goal_plausible is False:
        headline = _truncate(f"视觉复核存疑+{headline}", 64)

    reason_parts = []
    if vision.scene_summary:
        reason_parts.append(f"视觉:{_truncate(_sanitize(vision.scene_summary), 120)}")
    if environment.threats:
        reason_parts.append(f"环境:{_truncate(_threat_headline(environment.threats, 120), 120)}")
    if vision.error:
        reason_parts.append(f"视觉降级:{_sanitize(vision.error)}")

    return PerceptionConsensus(
        adopted_danger=adopted,
        vision=vision,
        environment=environment,
        agreement=agreement,
        action=action,
        headline=_truncate(headline, 64),
        reason=_truncate(" | ".join(reason_parts), 280),
        checked_at_ms=checked_at_ms,
        mode=mode,
    )
