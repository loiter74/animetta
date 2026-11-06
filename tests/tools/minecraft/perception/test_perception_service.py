"""Dual-perception service: capture + vision + environment + arbitration."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from animetta.tools.gamebot.contracts.v2 import Observation, Position
from animetta.tools.minecraft.perception.models import PerceptionDanger, VisionVerdict
from animetta.tools.minecraft.perception.service import (
    DualPerceptionService,
    describe_goal,
)
from animetta.tools.minecraft.voyager.goal_models import GoalSpec

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


def _goal() -> GoalSpec:
    return TypeAdapter(GoalSpec).validate_python(
        {
            "intent": "acquire",
            "target": "minecraft:iron_ingot",
            "quantity": 1,
            "constraints": {"dimension": "overworld"},
            "success_predicates": [
                {"kind": "inventory_at_least", "item": "iron_ingot", "quantity": 1}
            ],
        }
    )


class _Frame:
    def __init__(self, jpeg: bytes) -> None:
        self.jpeg = jpeg


class _StaticCapture:
    def __init__(self, frame: object | None) -> None:
        self._frame = frame
        self.calls = 0

    def capture(self) -> object | None:
        self.calls += 1
        return self._frame


class _StaticVision:
    def __init__(self, verdict: VisionVerdict) -> None:
        self._verdict = verdict
        self.prompts: list[str] = []
        self.images: list[bytes] = []

    async def judge(self, image_jpeg: bytes, prompt: str) -> VisionVerdict:
        self.images.append(image_jpeg)
        self.prompts.append(prompt)
        return self._verdict


def _service(
    capture: _StaticCapture,
    vision: _StaticVision,
) -> DualPerceptionService:
    return DualPerceptionService(
        capture=capture,
        vision=vision,
        now_ms=lambda: 42_000,
    )


class TestDescribeGoal:
    def test_none_goal_is_explicit(self) -> None:
        assert describe_goal(None) == "未提供目标"

    def test_goal_renders_intent_target_and_constraints(self) -> None:
        text = describe_goal(_goal())

        assert "获取" in text
        assert "iron_ingot" in text
        assert "minecraft:" not in text
        assert "dimension=overworld" in text


class TestDualPerceptionServiceMonitor:
    async def test_missing_window_degrades_vision_but_environment_halts(self) -> None:
        from animetta.tools.gamebot.contracts.v2 import DiscoverableEntity

        zombie_close = _observation(
            visible_entities=(
                DiscoverableEntity(
                    entity_id="e-1",
                    entity_type="minecraft:zombie",
                    position=Position(x=1.0, y=64.0, z=0.0),
                    health=10.0,
                ),
            )
        )
        service = _service(
            capture=_StaticCapture(None),
            vision=_StaticVision(VisionVerdict(available=True)),
        )

        consensus = await service.monitor(zombie_close)

        assert consensus.action == "halt"
        assert consensus.adopted_danger is PerceptionDanger.CRITICAL
        assert consensus.agreement is False
        assert consensus.headline.startswith("环境单感知")
        assert "spectator viewer window not found" in consensus.reason
        assert consensus.checked_at_ms == 42_000

    async def test_prompt_carries_goal_and_sensor_digest(self) -> None:
        vision = _StaticVision(VisionVerdict(available=True))
        service = _service(
            capture=_StaticCapture(_Frame(b"jpeg-bytes")),
            vision=vision,
        )

        consensus = await service.monitor(_observation(), goal=_goal())

        assert consensus.action == "continue"
        assert len(vision.prompts) == 1
        assert "获取 iron_ingot" in vision.prompts[0]
        assert "生命值=20.0/20" in vision.prompts[0]
        assert "饥饿=20/20" in vision.prompts[0]
        assert vision.images == [b"jpeg-bytes"]

    async def test_history_drives_stuck_detection(self) -> None:
        history = tuple(_observation() for _ in range(4))
        vision = _StaticVision(VisionVerdict(available=True))
        service = _service(
            capture=_StaticCapture(_Frame(b"jpeg-bytes")),
            vision=vision,
        )

        consensus = await service.monitor(_observation(), history)

        assert consensus.action == "alert"
        assert consensus.environment.stuck is True


class TestDualPerceptionServiceVerifyCompletion:
    async def test_implausible_goal_is_flagged_in_verify_mode(self) -> None:
        vision = _StaticVision(
            VisionVerdict(available=True, goal_plausible=False, scene_summary="目标物不在画面")
        )
        service = _service(
            capture=_StaticCapture(_Frame(b"jpeg-bytes")),
            vision=vision,
        )

        consensus = await service.verify_completion(_observation(), goal=_goal())

        assert consensus.mode == "verify_completion"
        assert consensus.action == "continue"
        assert consensus.headline.startswith("视觉复核存疑")
        assert "目标物不在画面" in consensus.reason
        assert "任务验收观察员" in vision.prompts[0]

    async def test_plausible_goal_passes_verify(self) -> None:
        vision = _StaticVision(VisionVerdict(available=True, goal_plausible=True))
        service = _service(
            capture=_StaticCapture(_Frame(b"jpeg-bytes")),
            vision=vision,
        )

        consensus = await service.verify_completion(_observation(), goal=None)

        assert consensus.mode == "verify_completion"
        assert consensus.action == "continue"
        assert "未提供目标" in vision.prompts[0]
