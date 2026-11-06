"""Safety-first arbitration between vision and environment verdicts."""

from __future__ import annotations

from animetta.tools.minecraft.perception.consensus import combine
from animetta.tools.minecraft.perception.models import (
    EnvironmentVerdict,
    PerceptionDanger,
    VisionVerdict,
)


def _vision(
    danger: PerceptionDanger = PerceptionDanger.NONE,
    *,
    available: bool = True,
    **overrides: object,
) -> VisionVerdict:
    return VisionVerdict(available=available, danger=danger, **overrides)  # type: ignore[arg-type]


def _environment(
    danger: PerceptionDanger = PerceptionDanger.NONE,
    *,
    available: bool = True,
    **overrides: object,
) -> EnvironmentVerdict:
    return EnvironmentVerdict(available=available, danger=danger, **overrides)  # type: ignore[arg-type]


class TestCombineActions:
    def test_both_safe_continues_with_agreement(self) -> None:
        consensus = combine(vision=_vision(), environment=_environment(), checked_at_ms=1_000)

        assert consensus.action == "continue"
        assert consensus.agreement is True
        assert consensus.adopted_danger is PerceptionDanger.NONE
        assert consensus.headline.startswith("双感知一致:安全")

    def test_environment_warning_alerts_without_agreement(self) -> None:
        consensus = combine(
            vision=_vision(),
            environment=_environment(PerceptionDanger.WARNING),
            checked_at_ms=1_000,
        )

        assert consensus.action == "alert"
        assert consensus.agreement is False
        assert consensus.adopted_danger is PerceptionDanger.WARNING
        assert consensus.headline.startswith("安全优先仲裁:告警")

    def test_single_agent_critical_halts(self) -> None:
        consensus = combine(
            vision=_vision(PerceptionDanger.CRITICAL),
            environment=_environment(),
            checked_at_ms=1_000,
        )

        assert consensus.action == "halt"
        assert consensus.agreement is False
        assert consensus.adopted_danger is PerceptionDanger.CRITICAL

    def test_vision_warning_plus_environment_critical_halts(self) -> None:
        consensus = combine(
            vision=_vision(PerceptionDanger.WARNING),
            environment=_environment(PerceptionDanger.CRITICAL),
            checked_at_ms=1_000,
        )

        assert consensus.action == "halt"
        assert consensus.adopted_danger is PerceptionDanger.CRITICAL
        assert consensus.agreement is False


class TestCombineDegradedAgents:
    def test_unavailable_vision_never_masks_environment_danger(self) -> None:
        consensus = combine(
            vision=_vision(available=False, error="ollama timeout"),
            environment=_environment(PerceptionDanger.CRITICAL),
            checked_at_ms=1_000,
        )

        assert consensus.action == "halt"
        assert consensus.adopted_danger is PerceptionDanger.CRITICAL
        assert consensus.agreement is False
        assert consensus.headline.startswith("环境单感知")
        assert "视觉降级:ollama timeout" in consensus.reason

    def test_unavailable_environment_defers_to_vision(self) -> None:
        consensus = combine(
            vision=_vision(PerceptionDanger.WARNING),
            environment=_environment(available=False),
            checked_at_ms=1_000,
        )

        assert consensus.action == "alert"
        assert consensus.adopted_danger is PerceptionDanger.WARNING
        assert consensus.headline.startswith("视觉单感知")


class TestCombinePresentation:
    def test_threats_merge_deduplicated_into_headline(self) -> None:
        consensus = combine(
            vision=_vision(PerceptionDanger.WARNING, threats=("岩浆", "重复")),
            environment=_environment(PerceptionDanger.WARNING, threats=("重复", "苦力怕")),
            checked_at_ms=1_000,
        )

        assert consensus.headline.startswith("双感知一致:告警")
        assert "岩浆" in consensus.headline
        assert "苦力怕" in consensus.headline
        assert consensus.headline.count("重复") == 1

    def test_headline_is_truncated_to_64_chars(self) -> None:
        long_threat = "很长的威胁描述" * 30
        consensus = combine(
            vision=_vision(PerceptionDanger.WARNING, threats=(long_threat, long_threat)),
            environment=_environment(PerceptionDanger.WARNING, threats=(long_threat,)),
            checked_at_ms=1_000,
        )

        assert len(consensus.headline) <= 64

    def test_reason_includes_scene_summary_and_environment_threats(self) -> None:
        consensus = combine(
            vision=_vision(PerceptionDanger.WARNING, scene_summary="岩浆湖边"),
            environment=_environment(PerceptionDanger.WARNING, threats=("lava:2.0m",)),
            checked_at_ms=1_000,
        )

        assert "视觉:岩浆湖边" in consensus.reason
        assert "环境:" in consensus.reason
        assert "lava:2.0m" in consensus.reason

    def test_secrets_and_control_characters_are_sanitized(self) -> None:
        consensus = combine(
            vision=_vision(
                PerceptionDanger.WARNING,
                scene_summary="密钥 sk-abcdef123456 泄露\n换行",
                threats=("威胁\r\n注入",),
            ),
            environment=_environment(PerceptionDanger.WARNING),
            checked_at_ms=1_000,
        )

        assert "sk-abcdef123456" not in consensus.reason
        assert "sk-abcdef123456" not in consensus.headline
        assert "\n" not in consensus.reason
        assert "\r" not in consensus.headline

    def test_checked_at_ms_is_carried_through(self) -> None:
        consensus = combine(vision=_vision(), environment=_environment(), checked_at_ms=123_456)

        assert consensus.checked_at_ms == 123_456


class TestCombineVerifyCompletion:
    def test_implausible_goal_is_flagged_but_not_downgraded(self) -> None:
        consensus = combine(
            vision=_vision(goal_plausible=False),
            environment=_environment(),
            checked_at_ms=1_000,
            mode="verify_completion",
        )

        assert consensus.mode == "verify_completion"
        assert consensus.action == "continue"
        assert consensus.headline.startswith("视觉复核存疑")

    def test_plausible_goal_has_no_doubt_prefix(self) -> None:
        consensus = combine(
            vision=_vision(goal_plausible=True),
            environment=_environment(),
            checked_at_ms=1_000,
            mode="verify_completion",
        )

        assert consensus.action == "continue"
        assert "视觉复核存疑" not in consensus.headline
