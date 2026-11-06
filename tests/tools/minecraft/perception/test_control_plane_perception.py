"""Control-plane integration of dual-perception monitoring and completion checks."""

from __future__ import annotations

import json
from pathlib import Path

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.perception.models import (
    EnvironmentVerdict,
    PerceptionConsensus,
    PerceptionDanger,
    VisionVerdict,
)
from animetta.tools.minecraft.voyager.budget import ExecutionBudget
from animetta.tools.minecraft.voyager.command_models import CommandState
from animetta.tools.minecraft.voyager.control_plane import UnifiedVoyagerController
from animetta.tools.minecraft.voyager.journal import CommandDraft, InMemoryCommandJournal
from animetta.tools.minecraft.voyager.scheduler import CommandExecutionError
from animetta.tools.minecraft.voyager.strategies.base import Complete

ROOT = Path(__file__).resolve().parents[4]
MESSAGES = json.loads(
    (ROOT / "contracts/gamebot/v2/fixtures/golden.json").read_text(encoding="utf-8")
)["messages"]


def _budget_dump() -> dict[str, object]:
    return ExecutionBudget(
        queue_timeout_ms=1_000,
        execution_timeout_ms=10_000,
        max_actions=16,
        max_strategy_attempts=4,
        max_travel_distance=256,
        max_blocks_changed=64,
        max_damage_taken=4,
    ).model_dump(mode="json")


def _consensus(
    danger: PerceptionDanger,
    *,
    mode: str = "monitor",
    checked_at_ms: int = 1_000,
) -> PerceptionConsensus:
    vision = VisionVerdict(available=True, danger=danger, scene_summary="画面安全")
    environment = EnvironmentVerdict(available=True, danger=danger)
    action = {PerceptionDanger.NONE: "continue", PerceptionDanger.WARNING: "alert"}.get(
        danger, "halt"
    )
    return PerceptionConsensus(
        adopted_danger=danger,
        vision=vision,
        environment=environment,
        action=action,  # type: ignore[arg-type]
        headline=f"测试共识:{danger.value}",
        checked_at_ms=checked_at_ms,
        mode=mode,  # type: ignore[arg-type]
    )


class _FakeRuntime:
    def __init__(self, manifest: RuntimeManifest, observation: Observation) -> None:
        self._manifest = manifest
        self._observation = observation

    async def get_manifest(self) -> RuntimeManifest:
        return self._manifest

    async def observe(self, _request: object) -> Observation:
        return self._observation


class _StubExecutor:
    def set_dispatch_observer(self, _observer: object) -> None:
        return None


class _CompleteStrategy:
    def __init__(self, output: dict[str, object] | None = None) -> None:
        self._output = output or {}

    def prepare(self, _goal: object) -> dict[str, object]:
        return {}

    def propose(self, _state: object, _observation: object) -> Complete:
        return Complete(output=dict(self._output))

    def accept_result(self, state: object, _feedback: object) -> object:
        return state


class _ScriptedPerception:
    def __init__(
        self,
        monitor: PerceptionConsensus,
        verify: PerceptionConsensus | None = None,
    ) -> None:
        self._monitor = monitor
        self._verify = verify
        self.monitor_calls = 0
        self.verify_calls = 0

    async def monitor(
        self,
        _observation: Observation,
        _history: tuple[Observation, ...],
        *,
        goal: object = None,
    ) -> PerceptionConsensus:
        self.monitor_calls += 1
        return self._monitor

    async def verify_completion(
        self, _observation: Observation, *, goal: object = None
    ) -> PerceptionConsensus:
        self.verify_calls += 1
        assert self._verify is not None
        return self._verify


async def _running_command(repository: InMemoryCommandJournal, *, mode: str = "mission") -> object:
    created = (
        await repository.create_command(
            CommandDraft(
                command_id=f"command-{mode}",
                caller_scope="principal:a",
                request_id="request-1",
                request_hash="a" * 64,
                kind="execute",
                mode=mode,
                payload={},
                requested_budget={},
                effective_budget=_budget_dump(),
                accepted_at_ms=1,
                execution_deadline_ms=2_000_000_000_000,
            )
        )
    )[0]
    return await repository.transition(
        created.command_id,
        expected_version=0,
        target=CommandState.RUNNING,
        reason_code="DISPATCHED",
        actor="worker",
        occurred_at_ms=2,
    )


def _controller(
    repository: InMemoryCommandJournal,
    *,
    perception: object | None = None,
    on_strategy_complete=None,
) -> UnifiedVoyagerController:
    return UnifiedVoyagerController(
        runtime=_FakeRuntime(
            RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"]),
            Observation.model_validate(MESSAGES["Observation"]),
        ),
        repository=repository,
        executor=_StubExecutor(),
        strategy_factories={"mission": lambda _manifest, _command: _CompleteStrategy()},
        on_strategy_complete=on_strategy_complete,
        make_id=lambda prefix: f"{prefix}-1",
        now_ms=lambda: 100,
        perception=perception,
        perception_interval_ms=60_000,
    )


class TestPerceptionSafetyHalt:
    async def test_critical_monitor_halts_command_with_consensus_output(self) -> None:
        repository = InMemoryCommandJournal()
        completed: list[dict[str, object]] = []

        async def on_strategy_complete(**kwargs: object) -> None:
            completed.append(kwargs)

        perception = _ScriptedPerception(monitor=_consensus(PerceptionDanger.CRITICAL))
        controller = _controller(
            repository, perception=perception, on_strategy_complete=on_strategy_complete
        )
        command = await _running_command(repository)

        try:
            await controller.execute_command(command)
            raise AssertionError("expected CommandExecutionError")
        except CommandExecutionError as exc:
            assert exc.reason_code == "PERCEPTION_SAFETY_HALT"
            assert exc.terminal_state is CommandState.FAILED
            assert exc.terminal_result is not None
            output = exc.terminal_result["output"]
            assert isinstance(output, dict)
            assert output["perception_consensus"]["adopted_danger"] == "critical"
            assert output["perception_consensus"]["headline"] == "测试共识:critical"

        assert perception.monitor_calls == 1
        assert perception.verify_calls == 0
        assert completed == []


class TestPerceptionCompletion:
    async def test_verify_consensus_rides_along_success_result(self) -> None:
        repository = InMemoryCommandJournal()
        completed: list[dict[str, object]] = []

        async def on_strategy_complete(**kwargs: object) -> None:
            completed.append(kwargs)

        perception = _ScriptedPerception(
            monitor=_consensus(PerceptionDanger.NONE),
            verify=_consensus(
                PerceptionDanger.WARNING, mode="verify_completion", checked_at_ms=2_000
            ),
        )
        controller = _controller(
            repository, perception=perception, on_strategy_complete=on_strategy_complete
        )
        command = await _running_command(repository)

        result = await controller.execute_command(command)

        assert perception.monitor_calls == 1
        assert perception.verify_calls == 1
        assert result is not None
        consensus = result["perception_consensus"]
        assert isinstance(consensus, dict)
        assert consensus["mode"] == "verify_completion"
        assert consensus["adopted_danger"] == "warning"
        assert "perception_alerts" not in result
        assert len(completed) == 1
        assert completed[0]["output"] == {}

    async def test_monitor_alerts_accumulate_into_completion_output(self) -> None:
        repository = InMemoryCommandJournal()
        perception = _ScriptedPerception(
            monitor=_consensus(PerceptionDanger.WARNING, checked_at_ms=1_500),
            verify=_consensus(PerceptionDanger.NONE, mode="verify_completion", checked_at_ms=2_500),
        )
        controller = _controller(repository, perception=perception)
        command = await _running_command(repository)

        result = await controller.execute_command(command)

        assert result is not None
        alerts = result["perception_alerts"]
        assert isinstance(alerts, list)
        assert len(alerts) == 1
        assert alerts[0]["adopted_danger"] == "warning"
        assert result["perception_consensus"]["adopted_danger"] == "none"

    async def test_perception_disabled_keeps_legacy_none_result(self) -> None:
        repository = InMemoryCommandJournal()
        completed: list[dict[str, object]] = []

        async def on_strategy_complete(**kwargs: object) -> None:
            completed.append(kwargs)

        controller = _controller(
            repository, perception=None, on_strategy_complete=on_strategy_complete
        )
        command = await _running_command(repository)

        result = await controller.execute_command(command)

        assert result is None
        assert len(completed) == 1


class TestPerceptionMonitoringCadence:
    async def test_monitor_runs_once_per_interval(self) -> None:
        repository = InMemoryCommandJournal()
        perception = _ScriptedPerception(monitor=_consensus(PerceptionDanger.NONE))
        controller = _controller(repository, perception=perception)
        command = await _running_command(repository)

        await controller.execute_command(command)

        # now_ms is pinned at 100: first check fires, the next is scheduled
        # for 60_100 and never re-arms during this single-decision command.
        assert perception.monitor_calls == 1
