"""Dual-perception service: local vision model plus deterministic environment judge."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, Protocol

from animetta.tools.gamebot.contracts.v2.observations import Observation
from animetta.tools.minecraft.voyager.goal_models import GoalSpec

from .capture import ViewerFrameCapture
from .consensus import combine
from .environment import EnvironmentJudge, EnvironmentThresholds
from .models import EnvironmentVerdict, PerceptionConsensus, VisionVerdict
from .ollama_vision import OllamaVisionClient

if TYPE_CHECKING:
    from animetta.tools.minecraft.core.config import MinecraftPerceptionConfig


class VisionClient(Protocol):
    """Minimal protocol so tests can substitute the Ollama client."""

    async def judge(self, image_jpeg: bytes, prompt: str) -> VisionVerdict: ...


class FrameCapture(Protocol):
    """Minimal protocol so tests can substitute window capture."""

    def capture(self) -> object | None: ...


def describe_goal(goal: GoalSpec | None) -> str:
    """Render a compact Chinese goal description for perception prompts."""

    if goal is None:
        return "未提供目标"
    intent_labels = {
        "acquire": "获取",
        "reach": "到达",
        "build": "建造",
        "survive": "生存",
        "explore": "探索",
    }
    intent = intent_labels.get(goal.intent, goal.intent)
    target = goal.target.removeprefix("minecraft:")
    constraints = [
        f"{key}={value}"
        for key, value in sorted(goal.constraints.items())
        if isinstance(value, (str, int, float, bool))
    ]
    suffix = f"（{'，'.join(constraints[:4])}）" if constraints else ""
    return f"{intent} {target}{suffix}"


def _environment_digest(verdict: EnvironmentVerdict, observation: Observation) -> str:
    health = observation.health
    food = observation.food
    position = observation.position
    parts = [f"生命值={health if health is not None else '未知'}/20"]
    parts.append(f"饥饿={food if food is not None else '未知'}/20")
    if position is not None:
        parts.append(f"坐标=({position.x:.0f},{position.y:.0f},{position.z:.0f})")
    if verdict.nearest_hostile_blocks is not None:
        parts.append(f"最近敌对生物={verdict.nearest_hostile_blocks:.1f}米")
    if verdict.threats:
        parts.append(f"结构化威胁={','.join(verdict.threats[:4])}")
    return "；".join(parts)


def _monitor_prompt(goal_text: str, digest: str) -> str:
    return (
        "你是 Minecraft 生存安全观察员，正在通过观战视角截图评估机器人当前处境。\n"
        f"当前任务目标：{goal_text}\n"
        f"机器人结构化传感器数据（可信）：{digest}\n"
        "请只依据画面内容判断危险等级：\n"
        "- critical：画面显示迫近的致命威胁（敌对生物贴身、岩浆/坠落/溺水的即时风险、被围攻）\n"
        "- warning：值得警惕但非立即致命（附近有敌对生物、生命值偏低、地形危险）\n"
        "- none：画面安全\n"
        "只输出一个 JSON 对象，不要输出其他文字：\n"
        '{"danger":"none|warning|critical","threats":["威胁1","威胁2"],'
        '"scene_summary":"一句话描述画面","confidence":0.0到1.0}'
    )


def _verify_prompt(goal_text: str, digest: str) -> str:
    return (
        "你是 Minecraft 任务验收观察员，正在通过观战视角截图复核任务是否真的完成。\n"
        f"任务目标：{goal_text}\n"
        f"机器人结构化传感器数据（可信）：{digest}\n"
        "规则判断已认定目标达成，请独立检查画面是否与该结论矛盾"
        "（例如目标物不在画面或周围环境明显不符）。\n"
        "只输出一个 JSON 对象，不要输出其他文字：\n"
        '{"danger":"none|warning|critical","threats":[],"scene_summary":"一句话描述画面",'
        '"goal_plausible":true或false,"confidence":0.0到1.0}'
    )


class DualPerceptionService:
    """Run both perception agents and merge them with safety-first arbitration."""

    def __init__(
        self,
        *,
        capture: FrameCapture,
        vision: VisionClient,
        thresholds: EnvironmentThresholds | None = None,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self._capture = capture
        self._vision = vision
        self._environment = EnvironmentJudge(thresholds)
        self._now_ms = now_ms

    def _timestamp(self) -> int:
        if self._now_ms is not None:
            return int(self._now_ms())
        import time

        return int(time.time() * 1000)

    async def _assess(
        self,
        *,
        observation: Observation,
        history: tuple[Observation, ...],
        prompt_builder: Callable[[str], str],
        mode: Literal["monitor", "verify_completion"],
    ) -> tuple[VisionVerdict, EnvironmentVerdict, PerceptionConsensus]:
        environment_verdict = self._environment.assess(observation, history)
        frame = await asyncio.to_thread(self._capture.capture)
        jpeg = getattr(frame, "jpeg", None)
        if isinstance(jpeg, bytes) and jpeg:
            prompt = prompt_builder(_environment_digest(environment_verdict, observation))
            vision_verdict = await self._vision.judge(jpeg, prompt)
        else:
            vision_verdict = VisionVerdict(
                available=False,
                model="",
                error="spectator viewer window not found",
            )
        consensus = combine(
            vision=vision_verdict,
            environment=environment_verdict,
            checked_at_ms=self._timestamp(),
            mode=mode,
        )
        return vision_verdict, environment_verdict, consensus

    async def monitor(
        self,
        observation: Observation,
        history: tuple[Observation, ...] = (),
        *,
        goal: GoalSpec | None = None,
    ) -> PerceptionConsensus:
        """Periodic in-execution safety check."""

        goal_text = describe_goal(goal)
        _, _, consensus = await self._assess(
            observation=observation,
            history=history,
            prompt_builder=lambda digest: _monitor_prompt(goal_text, digest),
            mode="monitor",
        )
        return consensus

    async def verify_completion(
        self,
        observation: Observation,
        *,
        goal: GoalSpec | None,
    ) -> PerceptionConsensus:
        """Corroborating visual check after rule-based goal verification."""

        goal_text = describe_goal(goal)
        _, _, consensus = await self._assess(
            observation=observation,
            history=(),
            prompt_builder=lambda digest: _verify_prompt(goal_text, digest),
            mode="verify_completion",
        )
        return consensus


def build_default_service(config: MinecraftPerceptionConfig) -> DualPerceptionService | None:
    """Construct the service from ``MinecraftPerceptionConfig`` when enabled."""

    if not getattr(config, "enabled", False):
        return None
    capture = ViewerFrameCapture(
        title_pattern=config.window_title_pattern,
        max_edge=config.vision_max_edge,
    )
    vision = OllamaVisionClient(
        base_url=config.ollama_base_url,
        model=config.vision_model,
        timeout_seconds=config.request_timeout_seconds,
    )
    thresholds = EnvironmentThresholds(
        health_critical=config.health_critical,
        health_warning=config.health_warning,
        food_critical=config.food_critical,
        hostile_warning_blocks=config.hostile_warning_blocks,
        hostile_critical_blocks=config.hostile_critical_blocks,
        creeper_critical_blocks=config.creeper_critical_blocks,
        hazard_warning_blocks=config.hazard_warning_blocks,
        hazard_critical_blocks=config.hazard_critical_blocks,
        stuck_radius=config.stuck_radius,
        stuck_minimum_samples=config.stuck_minimum_samples,
    )
    return DualPerceptionService(capture=capture, vision=vision, thresholds=thresholds)
