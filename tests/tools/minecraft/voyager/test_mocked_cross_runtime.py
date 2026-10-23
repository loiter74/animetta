"""Mocked acceptance chain across gateway, strategies, trust, status, and stop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.core.adapter import MinecraftGameBotV2Adapter
from animetta.tools.minecraft.skill.applicability import applicability_for_goal
from animetta.tools.minecraft.skill.trust import (
    SkillEnvironmentTrust,
    stable_environment_fingerprint,
)
from animetta.tools.minecraft.survival.registry import WorkflowRegistry
from animetta.tools.minecraft.survival.workflows import iron_survival_workflow
from animetta.tools.minecraft.voyager.budget import (
    BudgetAccount,
    BudgetUsage,
    ExecutionBudget,
    ModeBudgetPolicy,
)
from animetta.tools.minecraft.voyager.command_executor import CommandExecutor, ExecutorError
from animetta.tools.minecraft.voyager.command_models import CommandState
from animetta.tools.minecraft.voyager.gateway import ExecuteAtomicRequest, VoyagerGateway
from animetta.tools.minecraft.voyager.goal_models import AtomicAction, GoalSpec
from animetta.tools.minecraft.voyager.journal import CommandDraft, InMemoryCommandJournal
from animetta.tools.minecraft.voyager.stop import GlobalStopBarrier
from animetta.tools.minecraft.voyager.strategies.atomic import AtomicStrategy
from animetta.tools.minecraft.voyager.strategies.base import ExecuteStep
from animetta.tools.minecraft.voyager.strategies.fallback import FallbackStrategy
from animetta.tools.minecraft.voyager.strategies.learn import LearnStrategy
from animetta.tools.minecraft.voyager.strategies.live import LiveStrategy

ROOT = Path(__file__).resolve().parents[4]
MESSAGES = json.loads(
    (ROOT / "contracts/gamebot/v2/fixtures/golden.json").read_text(encoding="utf-8")
)["messages"]


def _goal() -> GoalSpec:
    return TypeAdapter(GoalSpec).validate_python(
        {
            "intent": "acquire",
            "target": "iron_ingot",
            "quantity": 1,
            "success_predicates": [
                {"kind": "inventory_at_least", "item": "iron_ingot", "quantity": 1}
            ],
        }
    )


def _budget() -> ExecutionBudget:
    return ExecutionBudget(
        queue_timeout_ms=1_000,
        execution_timeout_ms=10_000,
        max_actions=16,
        max_strategy_attempts=4,
        max_travel_distance=256,
        max_blocks_changed=64,
        max_damage_taken=4,
    )


async def _noop(*_args) -> None:
    return None


async def test_atomic_learn_validate_live_fallback_status_stop_chain() -> None:
    manifest = RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    observation = Observation.model_validate(MESSAGES["Observation"])

    atomic = AtomicStrategy(
        action=AtomicAction(capability="collect", parameters={"count": 1}),
        manifest=manifest,
    )
    assert atomic.propose(atomic.prepare(None), observation).kind == "execute"

    learn = LearnStrategy(
        resolve_frontier=lambda _goal: ("iron_ingot",),
        propose_node=lambda node: {
            "node": node,
            "capability": "collect",
            "parameters": {"count": 1},
            "maximum_cost": BudgetUsage(max_actions=1),
        },
        max_frontier_nodes=1,
        max_attempts=2,
        manifest=manifest,
        compilation_budget=_budget(),
        source_command_id="learn-command",
    )
    state = learn.prepare(_goal())
    state = learn.accept_result(state, {"receipt_hash": "a" * 64})
    state = learn.accept_result(state, {"receipt_hash": "b" * 64})
    learned = learn.propose(state, observation)
    revision = learned.output["candidate_revisions"][0]
    trust = SkillEnvironmentTrust.trusted(
        revision.revision_hash,
        stable_environment_fingerprint(manifest.profile),
        successes=1,
    )

    live = LiveStrategy(
        revisions={revision.revision_hash: revision},
        applicabilities={revision.revision_hash: applicability_for_goal(revision, _goal())},
        trusts=[trust],
        manifest=manifest,
    )
    assert live.propose(live.prepare(_goal()), observation).kind == "execute"

    registry = WorkflowRegistry()
    registry.register(iron_survival_workflow())
    fallback = FallbackStrategy(registry=registry)
    fallback_state = fallback.prepare(_goal())
    assert fallback.propose(fallback_state, observation).kind == "execute"
    assert fallback_state["learning_evidence_eligible"] is False

    repository = InMemoryCommandJournal()
    barrier = GlobalStopBarrier(repository=repository, signal_active=_noop, now_ms=lambda: 100)
    policy = ModeBudgetPolicy(atomic=_budget(), learn=_budget(), live=_budget(), fallback=_budget())
    gateway = VoyagerGateway(
        repository=repository,
        stop_barrier=barrier,
        manifest=manifest,
        budget_policy=policy,
        now_ms=lambda: 100,
        make_id=lambda prefix: f"{prefix}-acceptance",
    )
    handle = await gateway.execute(
        caller_scope="principal:acceptance",
        request=ExecuteAtomicRequest(
            contract_version="2",
            kind="atomic",
            request_id="acceptance-atomic",
            action=AtomicAction(capability="collect", parameters={"count": 1}),
        ),
    )
    status = await gateway.status(caller_scope="principal:acceptance")
    stopped = await gateway.stop(
        caller_scope="principal:acceptance",
        request_id="acceptance-stop",
        reason="acceptance complete",
    )

    assert status.commands[0].command_id == handle.command_id
    assert stopped.cancelled_command_ids == (handle.command_id,)


class _SentinelDispatchBridge:
    """Fake transport: golden manifest answers; dispatch is captured then fails."""

    def __init__(self) -> None:
        self.dispatched: list[dict] = []

    @property
    def is_running(self) -> bool:
        return True

    async def send_command(self, command: str, params: dict, *, timeout: float = 5.0) -> dict:
        if command == "gamebot_v2_manifest":
            return {"status": "success", "result": MESSAGES["RuntimeManifest"]}
        if command == "gamebot_v2_execute_action":
            self.dispatched.append(params)
            raise RuntimeError("dispatch sentinel: remaining_budget observed")
        raise AssertionError(f"unexpected transport command: {command}")


async def test_execute_step_dispatches_step_limited_remaining_budget() -> None:
    repository = InMemoryCommandJournal()
    bridge = _SentinelDispatchBridge()
    runtime = MinecraftGameBotV2Adapter(bridge)
    await runtime.get_manifest()
    created = (
        await repository.create_command(
            CommandDraft(
                command_id="command-budget",
                caller_scope="principal:budget",
                request_id="request-budget",
                request_hash="b" * 64,
                kind="execute",
                mode="atomic",
                payload={},
                requested_budget={},
                effective_budget={},
                accepted_at_ms=1,
                execution_deadline_ms=2_000_000_000_000,
            )
        )
    )[0]
    command = await repository.transition(
        created.command_id,
        expected_version=0,
        target=CommandState.RUNNING,
        reason_code="DISPATCHED",
        actor="worker",
        occurred_at_ms=2,
    )
    account = BudgetAccount(
        limit=ExecutionBudget(
            queue_timeout_ms=1_000,
            execution_timeout_ms=10_000,
            max_actions=8,
            max_strategy_attempts=4,
            max_travel_distance=512.0,
            max_blocks_changed=512,
            max_damage_taken=1.0,
            protected_items=frozenset({"minecraft:iron_pickaxe"}),
            resource_consumption={"coal": 10},
        )
    )
    step = ExecuteStep(
        capability="collect",
        parameters={"count": 1},
        maximum_cost=BudgetUsage(
            max_actions=1,
            max_travel_distance=96.0,
            max_blocks_changed=16,
            max_damage_taken=0.0,
            resource_consumption={"coal": 3},
        ),
    )
    executor = CommandExecutor(
        repository=repository,
        runtime=runtime,
        now_ms=lambda: 1_000,
        make_id=lambda prefix: f"{prefix}-budget",
    )
    with pytest.raises(ExecutorError) as caught:
        await executor.execute_step(
            command=command,
            step=step,
            before=Observation.model_validate(MESSAGES["Observation"]),
            ordinal=1,
            strategy_state_hash="state-hash",
            account=account,
        )
    assert caught.value.error.code == "RUNTIME_RESPONSE_LOST"
    assert "dispatch sentinel" in str(caught.value)

    assert len(bridge.dispatched) == 1
    step_cost = step.maximum_cost.model_dump(mode="json")
    remaining = bridge.dispatched[0]["remaining_budget"]
    assert {key: value for key, value in remaining.items() if key != "protected_items"} == step_cost
    assert remaining["protected_items"] == ["minecraft:iron_pickaxe"]

    journal_step = (await repository.list_steps(command.command_id))[0]
    assert journal_step.reservation == step_cost
    assert journal_step.state == "unknown"
