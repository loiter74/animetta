from __future__ import annotations

from importlib import import_module

import pytest
from pydantic import ValidationError

from animetta.tools.gamebot.contracts.v2.budget import BudgetVector
from animetta.tools.gamebot.contracts.v2.errors import RuntimeProtocolError
from animetta.tools.gamebot.contracts.v2.receipts import ActionReceipt, ReceiptOutcome
from animetta.tools.minecraft.mission.replan import (
    ObservationDigest,
    RebalanceProposal,
    VisionDigest,
    validate_rebalance,
)
from animetta.tools.minecraft.mission.repository import ObjectiveStatus
from animetta.tools.minecraft.voyager.budget import BudgetUsage

from .test_models import _cost, _mission_payload, _objective


def _rebalance_modules():
    return (
        import_module("animetta.tools.minecraft.mission.coordinator"),
        import_module("animetta.tools.minecraft.mission.state_machine"),
        import_module("animetta.tools.minecraft.mission.repository"),
    )


def _hex64(seed: str) -> str:
    import hashlib

    return hashlib.sha256(seed.encode()).hexdigest()


def _budget_exhausted_receipt(
    *, travel: float = 32.0, command_id: str = "mission-m-fight-zombie-v1"
) -> ActionReceipt:
    return ActionReceipt(
        receipt_id="receipt-001",
        command_id=command_id,
        step_id="step-001",
        correlation_id="corr-001",
        runtime_instance_id="runtime-001",
        capability="goto",
        parameter_hash=_hex64("params"),
        action_sequence=1,
        started_at_ms=1_000,
        finished_at_ms=2_000,
        started_tick=1,
        finished_tick=2,
        outcome=ReceiptOutcome.ERROR,
        error=RuntimeProtocolError(
            code="BUDGET_EXHAUSTED",
            message="travel budget exhausted",
            phase="budget",
            outcome_known=True,
            world_may_have_changed=True,
            caller_may_resubmit=False,
            operator_action="inspect budget accounting",
        ),
        post_observation="stable",
        reconciliation="accepted",
        goal_verification="failed",
        reconciliation_error=None,
        settlement_trace=(),
        before_observation_hash=_hex64("before"),
        after_observation_hash=_hex64("after"),
        budget_usage=BudgetVector(
            max_actions=2,
            max_strategy_attempts=2,
            max_travel_distance=travel,
            max_blocks_changed=0,
            max_damage_taken=0,
        ),
        content_hash=_hex64("content"),
    )


def _digests() -> tuple[ObservationDigest, VisionDigest]:
    return (
        ObservationDigest(
            position=(3.0, 52.0, 9.0),
            health=20.0,
            food=20.0,
            inventory={"cobblestone": 66},
            distance_travelled=32.0,
            blocks_changed=13,
            commands_issued=2,
            elapsed_ms=45_000,
        ),
        VisionDigest(
            consensus_action="alert",
            adopted_danger="none",
            mode="monitor",
            checked_at_ms=2_001,
        ),
    )


class _ScriptedPlanner:
    def __init__(self, proposal: RebalanceProposal | None) -> None:
        self.proposal = proposal
        self.requests: list[object] = []

    async def plan_rebalance(self, request):
        self.requests.append(request)
        return self.proposal


def _rebalance_mission_payload() -> dict[str, object]:
    payload = _mission_payload()
    payload["completion_predicates"] = []
    payload["autonomy"] = {
        "mode": "bounded",
        "allowed_domains": ["discovery"],
        "max_child_goals": 2,
        "max_new_skills": 0,
        "max_duration_ms": 600_000,
        "max_travel_distance": 256.0,
        "max_damage_taken": 6.0,
        "max_blocks_changed": 64,
        "max_budget_rebalances": 1,
        "stop_conditions": ["budget_exhausted"],
    }
    payload["objectives"] = [
        _objective("fight-zombie", budget=_cost(max_actions=4, max_travel_distance=32.0)),
        _objective("discover-copper", dependencies=["fight-zombie"], budget=_cost(max_actions=4)),
    ]
    return payload


async def _submit_mission(coordinator, repository, journal, payload):
    from animetta.tools.minecraft.mission.models import MissionSpec

    spec = MissionSpec.model_validate(payload)
    submitted = await coordinator.submit(
        caller_scope="conversation:user-001",
        request_id="request-001",
        spec=spec,
        occurred_at_ms=1_000,
    )
    return spec, submitted


async def _fail_command(journal, command_id: str, now: int) -> None:
    from animetta.tools.minecraft.voyager.command_models import CommandState

    queued = await journal.get_command(command_id)
    assert queued is not None
    running = await journal.transition(
        command_id,
        expected_version=queued.state_version,
        target=CommandState.RUNNING,
        reason_code="WORKER_CLAIMED",
        actor="worker",
        occurred_at_ms=now,
    )
    await journal.transition(
        command_id,
        expected_version=running.state_version,
        target=CommandState.FAILED,
        reason_code="BUDGET_EXHAUSTED",
        actor="controller",
        occurred_at_ms=now + 1,
    )


def test_validate_rebalance_accepts_growing_exhausted_dimension() -> None:
    request = type(
        "R",
        (),
        {
            "failed_objective": type(
                "O", (), {"budget": BudgetUsage(max_actions=4, max_travel_distance=32.0)}
            )(),
            "terminal_receipt": _budget_exhausted_receipt(),
        },
    )()
    proposal = RebalanceProposal(
        rationale="水岸距出发点比静态预估远，增加 travel 预算以完成取水返回。",
        new_budget=BudgetUsage(max_actions=4, max_travel_distance=64.0),
    )
    accepted = validate_rebalance(proposal=proposal, request=request)
    assert accepted.max_travel_distance == 64.0


def test_validate_rebalance_rejects_shrinking_dimension() -> None:
    request = type(
        "R",
        (),
        {
            "failed_objective": type(
                "O", (), {"budget": BudgetUsage(max_actions=4, max_travel_distance=32.0)}
            )(),
            "terminal_receipt": _budget_exhausted_receipt(),
        },
    )()
    proposal = RebalanceProposal(
        rationale="错误提议：缩小 travel。",
        new_budget=BudgetUsage(max_actions=2, max_travel_distance=48.0),
    )
    from animetta.tools.minecraft.mission.replan import RebalanceValidationError

    with pytest.raises(RebalanceValidationError, match="may not shrink"):
        validate_rebalance(proposal=proposal, request=request)


def test_validate_rebalance_rejects_no_growth() -> None:
    request = type(
        "R",
        (),
        {
            "failed_objective": type(
                "O", (), {"budget": BudgetUsage(max_actions=4, max_travel_distance=32.0)}
            )(),
            "terminal_receipt": _budget_exhausted_receipt(),
        },
    )()
    proposal = RebalanceProposal(
        rationale="无效提议：原样重试。",
        new_budget=BudgetUsage(max_actions=4, max_travel_distance=32.0),
    )
    from animetta.tools.minecraft.mission.replan import RebalanceValidationError

    with pytest.raises(RebalanceValidationError, match="must grow"):
        validate_rebalance(proposal=proposal, request=request)


def test_state_machine_permits_only_rebalance_retry_from_failed() -> None:
    _, state_machine, _ = _rebalance_modules()
    assert (
        state_machine.validate_objective_transition(
            ObjectiveStatus.FAILED, ObjectiveStatus.PENDING, reason_code="BUDGET_REBALANCED_RETRY"
        )
        is True
    )
    with pytest.raises(ValueError, match="BUDGET_REBALANCED_RETRY"):
        state_machine.validate_objective_transition(
            ObjectiveStatus.FAILED, ObjectiveStatus.PENDING, reason_code="MANUAL_RETRY"
        )


def test_autonomy_policy_bounds_rebalance_count() -> None:
    from animetta.tools.minecraft.mission.models import AutonomyPolicy

    assert AutonomyPolicy().max_budget_rebalances == 0
    with pytest.raises(ValidationError):
        AutonomyPolicy(mode="off", max_budget_rebalances=1)
    bounded = AutonomyPolicy.model_validate(
        {
            "mode": "bounded",
            "allowed_domains": ["discovery"],
            "max_child_goals": 2,
            "max_duration_ms": 600_000,
            "max_travel_distance": 256.0,
            "max_budget_rebalances": 2,
            "stop_conditions": ["budget_exhausted"],
        }
    )
    assert bounded.max_budget_rebalances == 2


async def test_request_rebalance_retries_objective_with_new_budget() -> None:
    coordinator_module, _, _ = _rebalance_modules()
    from animetta.tools.minecraft.mission.repository import InMemoryMissionRepository
    from animetta.tools.minecraft.voyager.journal import InMemoryCommandJournal

    repository = InMemoryMissionRepository()
    journal = InMemoryCommandJournal()
    await repository.connect()
    coordinator = coordinator_module.MissionCoordinator(repository=repository, journal=journal)
    spec, submitted = await _submit_mission(
        coordinator, repository, journal, _rebalance_mission_payload()
    )
    assert submitted.eligible_objective_id == "fight-zombie"

    await _fail_command(journal, submitted.eligible_command_id, 1_100)
    observation_digest, vision_digest = _digests()
    planner = _ScriptedPlanner(
        RebalanceProposal(
            rationale="视觉共识确认目标可达，代码感知显示实际路程 190 米超过静态 192-2 预算上限，提高 travel。",
            new_budget=BudgetUsage(
                max_actions=4,
                max_strategy_attempts=2,
                max_travel_distance=64.0,
                max_blocks_changed=0,
                max_damage_taken=2.0,
            ),
        )
    )
    outcome = await coordinator.request_rebalance(
        coordinator_module.VerifiedChildTransition(
            mission_id=spec.mission_id,
            objective_id="fight-zombie",
            command_id=submitted.eligible_command_id,
            command_state="failed",
            verification="failed",
            evidence_refs=("receipt:" + _hex64("content"),),
            actual_budget=BudgetUsage(max_actions=2, max_travel_distance=32.0),
            occurred_at_ms=1_200,
        ),
        planner=planner,
        observation_digest=observation_digest,
        vision_digest=vision_digest,
        terminal_receipt=_budget_exhausted_receipt(command_id=submitted.eligible_command_id),
    )

    assert outcome == "rebalanced"
    assert len(planner.requests) == 1
    snapshot = await repository.snapshot(spec.mission_id)
    fight = next(
        item for item in snapshot.objectives if item.objective.objective_id == "fight-zombie"
    )
    assert fight.status is ObjectiveStatus.ACTIVE
    assert fight.objective.budget.max_travel_distance == 64.0
    assert snapshot.mission.status == "running"
    assert snapshot.budget is not None
    assert any(
        key.startswith("objective:fight-zombie:rebalance") for key in snapshot.budget.reservations
    )
    retry_command = await journal.get_command(
        f"mission-{spec.mission_id}-fight-zombie-v{fight.version}"
    )
    assert retry_command is not None
    assert retry_command.requested_budget["max_travel_distance"] == 64.0


async def test_request_rebalance_terminal_when_planner_declines() -> None:
    coordinator_module, _, _ = _rebalance_modules()
    from animetta.tools.minecraft.mission.repository import (
        InMemoryMissionRepository,
        MissionStatus,
    )
    from animetta.tools.minecraft.voyager.journal import InMemoryCommandJournal

    repository = InMemoryMissionRepository()
    journal = InMemoryCommandJournal()
    await repository.connect()
    coordinator = coordinator_module.MissionCoordinator(repository=repository, journal=journal)
    spec, submitted = await _submit_mission(
        coordinator, repository, journal, _rebalance_mission_payload()
    )

    await _fail_command(journal, submitted.eligible_command_id, 1_100)
    observation_digest, vision_digest = _digests()
    outcome = await coordinator.request_rebalance(
        coordinator_module.VerifiedChildTransition(
            mission_id=spec.mission_id,
            objective_id="fight-zombie",
            command_id=submitted.eligible_command_id,
            command_state="failed",
            verification="failed",
            evidence_refs=("receipt:" + _hex64("content"),),
            actual_budget=BudgetUsage(max_actions=2, max_travel_distance=32.0),
            occurred_at_ms=1_200,
        ),
        planner=_ScriptedPlanner(None),
        observation_digest=observation_digest,
        vision_digest=vision_digest,
        terminal_receipt=_budget_exhausted_receipt(command_id=submitted.eligible_command_id),
    )

    assert outcome == "terminal_failed"
    snapshot = await repository.snapshot(spec.mission_id)
    assert snapshot.mission.status is MissionStatus.FAILED
    fight = next(
        item for item in snapshot.objectives if item.objective.objective_id == "fight-zombie"
    )
    assert fight.status is ObjectiveStatus.FAILED


async def test_request_rebalance_not_applicable_when_policy_disallows() -> None:
    coordinator_module, _, _ = _rebalance_modules()
    from animetta.tools.minecraft.mission.repository import InMemoryMissionRepository
    from animetta.tools.minecraft.voyager.journal import InMemoryCommandJournal

    repository = InMemoryMissionRepository()
    journal = InMemoryCommandJournal()
    await repository.connect()
    coordinator = coordinator_module.MissionCoordinator(repository=repository, journal=journal)
    payload = _rebalance_mission_payload()
    payload["autonomy"] = dict(payload["autonomy"], max_budget_rebalances=0)  # type: ignore[arg-type]
    spec, submitted = await _submit_mission(coordinator, repository, journal, payload)

    await _fail_command(journal, submitted.eligible_command_id, 1_100)
    observation_digest, vision_digest = _digests()
    outcome = await coordinator.request_rebalance(
        coordinator_module.VerifiedChildTransition(
            mission_id=spec.mission_id,
            objective_id="fight-zombie",
            command_id=submitted.eligible_command_id,
            command_state="failed",
            verification="failed",
            evidence_refs=("receipt:" + _hex64("content"),),
            actual_budget=BudgetUsage(max_actions=2, max_travel_distance=32.0),
            occurred_at_ms=1_200,
        ),
        planner=_ScriptedPlanner(None),
        observation_digest=observation_digest,
        vision_digest=vision_digest,
        terminal_receipt=_budget_exhausted_receipt(command_id=submitted.eligible_command_id),
    )

    assert outcome == "not_applicable"


async def test_second_budget_exhaustion_exhausts_rebalance_window() -> None:
    coordinator_module, _, _ = _rebalance_modules()
    from animetta.tools.minecraft.mission.repository import InMemoryMissionRepository
    from animetta.tools.minecraft.voyager.journal import InMemoryCommandJournal

    repository = InMemoryMissionRepository()
    journal = InMemoryCommandJournal()
    await repository.connect()
    coordinator = coordinator_module.MissionCoordinator(repository=repository, journal=journal)
    spec, submitted = await _submit_mission(
        coordinator, repository, journal, _rebalance_mission_payload()
    )
    planner = _ScriptedPlanner(
        RebalanceProposal(
            rationale="第一次重分配。",
            new_budget=BudgetUsage(
                max_actions=4,
                max_strategy_attempts=2,
                max_travel_distance=64.0,
                max_blocks_changed=0,
                max_damage_taken=2.0,
            ),
        )
    )

    async def exhaust_once(command_id: str, travel: float) -> str:
        await _fail_command(journal, command_id, 1_100)
        observation_digest, vision_digest = _digests()
        return await coordinator.request_rebalance(
            coordinator_module.VerifiedChildTransition(
                mission_id=spec.mission_id,
                objective_id="fight-zombie",
                command_id=command_id,
                command_state="failed",
                verification="failed",
                evidence_refs=("receipt:" + _hex64("content"),),
                actual_budget=BudgetUsage(max_actions=2, max_travel_distance=travel),
                occurred_at_ms=1_200,
            ),
            planner=planner,
            observation_digest=observation_digest,
            vision_digest=vision_digest,
            terminal_receipt=_budget_exhausted_receipt(command_id=command_id, travel=travel),
        )

    first = await exhaust_once(submitted.eligible_command_id, 32.0)
    assert first == "rebalanced"
    snapshot = await repository.snapshot(spec.mission_id)
    fight = next(
        item for item in snapshot.objectives if item.objective.objective_id == "fight-zombie"
    )
    retry_command_id = f"mission-{spec.mission_id}-fight-zombie-v{fight.version}"
    second = await exhaust_once(retry_command_id, 64.0)
    assert second == "not_applicable"
