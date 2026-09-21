"""Pure exploration rules; no transport, graph, model or map imports."""

import re
from dataclasses import dataclass
from typing import Literal


def explicit_intent(
    text: str,
) -> Literal["observe", "pause", "continue", "retract", "identify"] | None:
    """Safety/control language takes precedence over a model or remote search."""
    value = text.strip().strip("。！？!?，,. ")
    if value in {"等一下", "等等", "停", "停一下", "暂停", "先别动", "stop", "pause"}:
        return "pause"
    if value in {"继续", "继续吧", "再放大", "再放大下", "放大一点", "continue"}:
        return "continue"
    if value.startswith(("不是", "不对", "搞错", "认错")):
        return "retract"
    if any(word in value for word in ("经常走", "很熟悉", "我认得", "住的地方")):
        return "identify"
    if any(word in value for word in ("干什么", "用途", "这是什么", "什么地方")):
        return "observe"
    return None


def fallback_query(text: str) -> str:
    return re.sub(r"^(?:我记得|好像|大概|应该|可能)?(?:是在|是|在)?", "", text.strip()).strip(
        "？?。 "
    )[:200]


@dataclass(frozen=True)
class ExplorationRules:
    feedback_seconds: float = 5.0
    reading_seconds: float = 7.0
    max_steps: int = 3
    max_seconds: float = 60.0

    def can_continue(
        self, *, selected: bool, steps: int, started: float, now: float, phase: str
    ) -> bool:
        return (
            selected
            and phase == "feedback"
            and steps < self.max_steps
            and 0 <= now - started < self.max_seconds
        )
