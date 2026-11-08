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

from .test_models import _combat_goal, _cost, _mission_payload, _objective


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


def _deadline_receipt(command_id: str = "mission-m-fight-zombie-v1") -> ActionReceipt:
    return _budget_exhausted_receipt(command_id=command_id, travel=5.0).model_copy(
        update={
            "error": RuntimeProtocolError(
                code="ACTION_DEADLINE_EXPIRED",
                message="pathfinder navigation did not finish before its deadline",
                phase="runtime",
                outcome_known=True,
                world_may_have_changed=True,
                caller_may_resubmit=False,
                operator_action="inspect navigation trace",
            )
        }
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


def test_validate_rebalance_accepts_shrinking_non_exhausted_dimension() -> None:
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
        rationale="travel 撞墙，缩小 actions 档位换取行程余量（账户内的真重分配）。",
        new_budget=BudgetUsage(max_actions=2, max_travel_distance=48.0),
    )
    accepted = validate_rebalance(proposal=proposal, request=request)
    assert accepted.max_actions == 2 and accepted.max_travel_distance == 48.0


def test_validate_rebalance_rejects_growing_non_exhausted_dimension() -> None:
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
        rationale="错误提议：顺带扩大未耗尽的 actions。",
        new_budget=BudgetUsage(max_actions=8, max_travel_distance=64.0),
    )
    from animetta.tools.minecraft.mission.replan import RebalanceValidationError

    with pytest.raises(RebalanceValidationError, match="may not grow non-exhausted"):
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

    with pytest.raises(RebalanceValidationError, match="must strictly grow"):
        validate_rebalance(proposal=proposal, request=request)


def _deadline_request():
    return type(
        "R",
        (),
        {
            "failed_objective": type(
                "O", (), {"budget": BudgetUsage(max_actions=4, max_travel_distance=32.0)}
            )(),
            "terminal_receipt": _deadline_receipt(),
        },
    )()


def test_validate_rebalance_deadline_class_requires_navigation_timeout() -> None:
    from animetta.tools.minecraft.mission.replan import RebalanceValidationError

    proposal = RebalanceProposal(
        rationale="无效提议：无耗尽维度却未给出导航时限。",
        new_budget=BudgetUsage(max_actions=4, max_travel_distance=32.0),
    )
    with pytest.raises(RebalanceValidationError, match="requires navigation_timeout_ms"):
        validate_rebalance(proposal=proposal, request=_deadline_request())


def test_validate_rebalance_deadline_class_rejects_budget_drift() -> None:
    from animetta.tools.minecraft.mission.replan import RebalanceValidationError

    proposal = RebalanceProposal(
        rationale="无效提议：借时限之名扩大预算。",
        new_budget=BudgetUsage(max_actions=4, max_travel_distance=64.0),
        navigation_timeout_ms=90_000,
    )
    with pytest.raises(RebalanceValidationError, match="may not grow dimension"):
        validate_rebalance(proposal=proposal, request=_deadline_request())


def test_validate_rebalance_deadline_class_accepts_affordable_smaller_envelope() -> None:
    request = _deadline_request()
    proposal = RebalanceProposal(
        rationale="旧 travel 包络超出账户剩余，降到剩余额度内重走。",
        new_budget=BudgetUsage(max_actions=4, max_travel_distance=24.0),
        navigation_timeout_ms=90_000,
    )
    accepted = validate_rebalance(proposal=proposal, request=request)
    assert accepted.max_travel_distance == 24.0


def test_validate_rebalance_rejects_exceeding_account_remaining() -> None:
    request = type(
        "R",
        (),
        {
            "failed_objective": type(
                "O", (), {"budget": BudgetUsage(max_actions=4, max_travel_distance=32.0)}
            )(),
            "terminal_receipt": _deadline_receipt(),
            "remaining_budget": BudgetUsage(max_actions=4, max_travel_distance=20.0),
        },
    )()
    proposal = RebalanceProposal(
        rationale="旧包络 32 超过账户剩余 20，仍按旧值提交。",
        new_budget=BudgetUsage(max_actions=4, max_travel_distance=32.0),
        navigation_timeout_ms=90_000,
    )
    from animetta.tools.minecraft.mission.replan import RebalanceValidationError

    with pytest.raises(RebalanceValidationError, match="remaining 'max_travel_distance'"):
        validate_rebalance(proposal=proposal, request=request)


def test_validate_rebalance_deadline_class_accepts_pure_timeout_extension() -> None:
    request = _deadline_request()
    proposal = RebalanceProposal(
        rationale="导航在持续推进（砂砾回填段挖搭有真实进展），延长导航时限而非预算。",
        new_budget=request.failed_objective.budget.model_copy(),
        navigation_timeout_ms=90_000,
    )
    accepted = validate_rebalance(proposal=proposal, request=request)
    assert accepted.max_travel_distance == 32.0


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
    assert planner.requests[0].remaining_budget is not None
    assert (
        planner.requests[0].remaining_budget.max_travel_distance <= spec.budget.max_travel_distance
    )
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


async def test_request_rebalance_deadline_class_extends_navigation_timeout() -> None:
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
    snapshot = await repository.snapshot(spec.mission_id)
    fight_before = next(
        item for item in snapshot.objectives if item.objective.objective_id == "fight-zombie"
    )
    unchanged_budget = fight_before.objective.budget.model_copy()

    await _fail_command(journal, submitted.eligible_command_id, 1_100)
    observation_digest, vision_digest = _digests()
    planner = _ScriptedPlanner(
        RebalanceProposal(
            rationale="导航轨迹显示持续进展但被 30 秒段级时限收尸（r114 砂砾回填爬升），延长导航时限。",
            new_budget=unchanged_budget,
            navigation_timeout_ms=90_000,
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
        terminal_receipt=_deadline_receipt(submitted.eligible_command_id),
    )

    assert outcome == "rebalanced"
    snapshot = await repository.snapshot(spec.mission_id)
    fight = next(
        item for item in snapshot.objectives if item.objective.objective_id == "fight-zombie"
    )
    assert fight.status is ObjectiveStatus.ACTIVE
    assert fight.objective.goal.constraints["navigation_timeout_ms"] == 90_000
    assert fight.objective.budget == unchanged_budget


async def test_request_rebalance_clamps_enforced_stop_overshoot() -> None:
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

    await _fail_command(journal, submitted.eligible_command_id, 1_100)
    observation_digest, vision_digest = _digests()
    planner = _ScriptedPlanner(
        RebalanceProposal(
            rationale="执法停止本身超支 1.5 米（r165 形态）：按账户剩余提出可负担重试包络。",
            new_budget=BudgetUsage(max_actions=4, max_travel_distance=64.0),
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
            actual_budget=BudgetUsage(max_actions=2, max_travel_distance=33.5),
            terminal_error_code="BUDGET_EXHAUSTED",
            occurred_at_ms=1_200,
        ),
        planner=planner,
        observation_digest=observation_digest,
        vision_digest=vision_digest,
        terminal_receipt=_budget_exhausted_receipt(command_id=submitted.eligible_command_id),
    )

    assert outcome == "rebalanced"
    assert planner.requests[0].remaining_budget is not None
    # 256 total - 32 clamped settle - 32 discover-copper open reservation;
    # an unclamped settle would leave 191.5.
    assert planner.requests[0].remaining_budget.max_travel_distance == pytest.approx(192.0)
    snapshot = await repository.snapshot(spec.mission_id)
    assert snapshot.mission.status == "running"


async def test_request_rebalance_overshoot_without_enforced_stop_violates() -> None:
    coordinator_module, _, _ = _rebalance_modules()
    from animetta.tools.minecraft.mission.repository import InMemoryMissionRepository
    from animetta.tools.minecraft.voyager.budget import BudgetContractViolationError
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
    planner = _ScriptedPlanner(None)
    with pytest.raises(BudgetContractViolationError, match="usage exceeds reservation"):
        await coordinator.request_rebalance(
            coordinator_module.VerifiedChildTransition(
                mission_id=spec.mission_id,
                objective_id="fight-zombie",
                command_id=submitted.eligible_command_id,
                command_state="failed",
                verification="failed",
                evidence_refs=("receipt:" + _hex64("content"),),
                actual_budget=BudgetUsage(max_actions=2, max_travel_distance=33.5),
                terminal_error_code=None,
                occurred_at_ms=1_200,
            ),
            planner=planner,
            observation_digest=observation_digest,
            vision_digest=vision_digest,
            terminal_receipt=_budget_exhausted_receipt(command_id=submitted.eligible_command_id),
        )
    assert planner.requests == []


def test_mission_strategy_injects_navigation_timeout_into_goto_steps() -> None:
    from animetta.tools.minecraft.voyager.goal_models import CombatGoal
    from animetta.tools.minecraft.voyager.strategies.base import ExecuteStep
    from animetta.tools.minecraft.voyager.strategies.mission import MissionStrategy

    class _GotoStrategy:
        def prepare(self, goal):
            return {}

        def propose(self, state, observation):
            return ExecuteStep(
                capability="goto",
                parameters={"x": 35, "y": 63, "z": 11},
                maximum_cost=BudgetUsage(max_actions=2),
            )

    goal = CombatGoal.model_validate(
        {**_combat_goal(), "constraints": {"navigation_timeout_ms": 90_000}}
    )
    strategy = MissionStrategy(live=_GotoStrategy(), learn=_GotoStrategy(), fallback=None)
    state = strategy.prepare(goal)
    decision = strategy.propose(state, None)
    assert decision.parameters["navigation_timeout_ms"] == 90_000
    assert decision.parameters["x"] == 35


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


def test_state_machine_allows_audited_same_state_replace_on_failed() -> None:
    _, state_machine_module, repository_module = _rebalance_modules()

    assert (
        state_machine_module.validate_objective_transition(
            ObjectiveStatus.FAILED,
            ObjectiveStatus.FAILED,
            reason_code="BUDGET_REBALANCED_RETRY",
        )
        is True
    )
    with pytest.raises(ValueError, match="illegal objective transition"):
        state_machine_module.validate_objective_transition(
            ObjectiveStatus.FAILED,
            ObjectiveStatus.FAILED,
            reason_code="CHILD_VERIFICATION_FAILED",
        )
    assert repository_module.ObjectiveStatus.FAILED is ObjectiveStatus.FAILED


async def test_on_child_transition_is_idempotent_when_rebalance_chain_already_failed_objective() -> (
    None
):
    """r124 regression: the chain failed after its planner; the replayed child
    transition must finish mission-level REQUIRED_CHILD_FAILED accounting
    instead of stranding the mission in running until the harness grace expires."""
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
    # The chain runs, settles, transitions the objective to FAILED itself, then
    # its planner declines -> terminal_failed (mission already FAILED here).
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

    # Now the r124 replay scenario: the chain instead THREW after transitioning
    # the objective (planner proposal accepted then replace raised). Rebuild
    # that state: objective already FAILED, mission still running, and the
    # fallback on_child_transition arrives with the same child failure.
    repository2 = InMemoryMissionRepository()
    journal2 = InMemoryCommandJournal()
    await repository2.connect()
    coordinator2 = coordinator_module.MissionCoordinator(repository=repository2, journal=journal2)
    spec2, submitted2 = await _submit_mission(
        coordinator2, repository2, journal2, _rebalance_mission_payload()
    )
    await _fail_command(journal2, submitted2.eligible_command_id, 1_100)
    snapshot = await repository2.snapshot(spec2.mission_id)
    await repository2.transition_objective(
        spec2.mission_id,
        "fight-zombie",
        expected_version=next(
            item for item in snapshot.objectives if item.objective.objective_id == "fight-zombie"
        ).version,
        target=ObjectiveStatus.FAILED,
        reason_code="BUDGET_EXHAUSTED_CHILD",
        actor="mission-coordinator",
        occurred_at_ms=1_150,
        details={},
        evidence_refs=(),
    )

    result = await coordinator2.on_child_transition(
        coordinator_module.VerifiedChildTransition(
            mission_id=spec2.mission_id,
            objective_id="fight-zombie",
            command_id=submitted2.eligible_command_id,
            command_state="failed",
            verification="failed",
            evidence_refs=("receipt:" + _hex64("content"),),
            actual_budget=BudgetUsage(max_actions=2, max_travel_distance=32.0),
            occurred_at_ms=1_200,
        )
    )

    assert result.mission_status is MissionStatus.FAILED
    final = await repository2.snapshot(spec2.mission_id)
    assert final.mission.status is MissionStatus.FAILED


async def test_rebalanced_retry_success_completes_objective_and_advances() -> None:
    """r127 regression: after a rebalance retry SUCCEEDS, on_child_transition must
    settle the rebalance reservation, complete the objective, and advance to the
    next objective — the r127 run stranded the mission in running because the
    rebalance reservation id was invisible to the standard settle lookup."""
    coordinator_module, _, _ = _rebalance_modules()
    from animetta.tools.minecraft.mission.repository import InMemoryMissionRepository, MissionStatus
    from animetta.tools.minecraft.voyager.command_models import CommandState
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
        planner=_ScriptedPlanner(
            RebalanceProposal(
                rationale="重试包络：吸收已花费后仍可负担。",
                new_budget=BudgetUsage(
                    max_actions=4,
                    max_strategy_attempts=2,
                    max_travel_distance=64.0,
                    max_blocks_changed=0,
                    max_damage_taken=2.0,
                ),
            )
        ),
        observation_digest=observation_digest,
        vision_digest=vision_digest,
        terminal_receipt=_budget_exhausted_receipt(command_id=submitted.eligible_command_id),
    )
    assert outcome == "rebalanced"
    snapshot = await repository.snapshot(spec.mission_id)
    fight = next(
        item for item in snapshot.objectives if item.objective.objective_id == "fight-zombie"
    )
    retry_command_id = f"mission-{spec.mission_id}-fight-zombie-v{fight.version}"

    # The retry command runs and succeeds.
    queued = await journal.get_command(retry_command_id)
    assert queued is not None
    running = await journal.transition(
        retry_command_id,
        expected_version=queued.state_version,
        target=CommandState.RUNNING,
        reason_code="WORKER_CLAIMED",
        actor="worker",
        occurred_at_ms=1_300,
    )
    await journal.transition(
        retry_command_id,
        expected_version=running.state_version,
        target=CommandState.SUCCEEDED,
        reason_code="VERIFIED",
        actor="worker",
        occurred_at_ms=1_400,
    )

    result = await coordinator.on_child_transition(
        coordinator_module.VerifiedChildTransition(
            mission_id=spec.mission_id,
            objective_id="fight-zombie",
            command_id=retry_command_id,
            command_state="succeeded",
            verification="verified",
            evidence_refs=("receipt:" + _hex64("retry"),),
            actual_budget=BudgetUsage(max_actions=1, max_travel_distance=8.0),
            occurred_at_ms=1_500,
        )
    )

    assert result.mission_status is MissionStatus.RUNNING
    final = await repository.snapshot(spec.mission_id)
    fight_after = next(
        item for item in final.objectives if item.objective.objective_id == "fight-zombie"
    )
    assert fight_after.status is ObjectiveStatus.COMPLETED
    copper = next(
        item for item in final.objectives if item.objective.objective_id == "discover-copper"
    )
    assert copper.status is ObjectiveStatus.ACTIVE
    assert final.mission.status is MissionStatus.RUNNING
    assert final.budget is not None
    assert not any(key.startswith("objective:fight-zombie") for key in final.budget.reservations)
    copper_command = await journal.get_command(
        f"mission-{spec.mission_id}-discover-copper-v{copper.version}"
    )
    assert copper_command is not None
