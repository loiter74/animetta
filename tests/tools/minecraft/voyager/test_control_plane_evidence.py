"""The controller gathers authoritative evidence before declaring a goal complete."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from animetta.tools.gamebot.contracts.v2 import (
    ActionReceipt,
    Observation,
    ReceiptOutcome,
    RuntimeManifest,
)
from animetta.tools.minecraft.blueprint import (
    BlueprintBinding,
    BlueprintCompiler,
    starter_shelter_blueprint,
)
from animetta.tools.minecraft.discovery import (
    InMemoryWorldFactStore,
    RuntimeDiscoveryProjector,
    WorldFactState,
)
from animetta.tools.minecraft.voyager.budget import BudgetAccount, BudgetUsage, ExecutionBudget
from animetta.tools.minecraft.voyager.command_executor import (
    ExecutorError,
    ReconciliationResult,
    StepExecutionResult,
)
from animetta.tools.minecraft.voyager.command_models import (
    CommandState,
    ControlPlaneError,
)
from animetta.tools.minecraft.voyager.control_plane import UnifiedVoyagerController
from animetta.tools.minecraft.voyager.goal_evidence import (
    GoalEvidence,
    RuntimeGoalEvidenceCollector,
)
from animetta.tools.minecraft.voyager.goal_models import GoalSpec
from animetta.tools.minecraft.voyager.journal import JournalCommand
from animetta.tools.minecraft.voyager.reconciliation import RecoveryDecision
from animetta.tools.minecraft.voyager.scheduler import CommandExecutionError
from animetta.tools.minecraft.voyager.strategies.base import Complete, ExecuteStep

ROOT = Path(__file__).resolve().parents[4]
MESSAGES = json.loads(
    (ROOT / "contracts/gamebot/v2/fixtures/golden.json").read_text(encoding="utf-8")
)["messages"]


class RuntimeStub:
    runtime_instance_id = "runtime-instance-1"
    is_running = True

    def __init__(self) -> None:
        self.manifest = RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
        self.observation = Observation.model_validate(MESSAGES["Observation"])

    async def get_manifest(self):
        return self.manifest

    async def observe(self, request):
        del request
        return self.observation


class ExecutorStub:
    def set_dispatch_observer(self, observer):
        self.observer = observer


class ActivityRecorderStub:
    def __init__(self) -> None:
        self.phases: list[str] = []

    async def record_command(self, _command, *, phase, **_kwargs):
        self.phases.append(phase)


class CompleteStrategy:
    def prepare(self, goal):
        return {"goal": goal}

    def propose(self, state, observation):
        del state, observation
        return Complete(output={"compiled_blueprints": ()})

    def accept_result(self, state, result):  # pragma: no cover - no steps
        raise AssertionError((state, result))


class EvidenceCollectorStub:
    def __init__(self) -> None:
        self.called = False

    async def collect(self, **kwargs):
        assert kwargs["output"] == {"compiled_blueprints": ()}
        self.called = True
        return GoalEvidence(technology_evidence=("technology:stone-age",))


class VerifierStub:
    def __init__(self) -> None:
        self.received = None

    def verify(self, **kwargs):
        self.received = kwargs
        return {"satisfied": True, "predicate_results": [], "evidence_hashes": []}


def _goal():
    return TypeAdapter(GoalSpec).validate_python(
        {
            "intent": "survive",
            "target": "stay healthy",
            "success_predicates": [{"kind": "health_at_least", "health": 1}],
        }
    )


def _command() -> JournalCommand:
    budget = ExecutionBudget(
        queue_timeout_ms=1_000,
        execution_timeout_ms=10_000,
        max_actions=1,
        max_strategy_attempts=1,
        max_travel_distance=1,
        max_blocks_changed=0,
        max_damage_taken=0,
    )
    return JournalCommand(
        command_id="mission-m1-objective-v1",
        caller_scope="session:one",
        request_id="request-1",
        request_hash="a" * 64,
        kind="execute",
        mode="mission",
        payload={"goal": _goal().model_dump(mode="json")},
        requested_budget=budget.model_dump(mode="json"),
        effective_budget=budget.model_dump(mode="json"),
        accepted_at_ms=1,
        queue_deadline_ms=2_000,
        execution_deadline_ms=10_000,
        queue_sequence=1,
        state=CommandState.RUNNING,
        state_version=2,
        started_at_ms=2,
    )


async def test_missing_failed_command_has_empty_projected_evidence() -> None:
    collector = RuntimeGoalEvidenceCollector(
        runtime=object(),
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 1,
        world_fact_store=object(),
        advancement_store=object(),
    )

    assert await collector.current_world_facts("failed-before-evidence") == ()
    assert await collector.current_advancement_events("failed-before-evidence") == ()


async def test_controller_passes_collected_typed_evidence_to_goal_verifier() -> None:
    collector = EvidenceCollectorStub()
    verifier = VerifierStub()
    activity = ActivityRecorderStub()
    controller = UnifiedVoyagerController(
        runtime=RuntimeStub(),
        repository=object(),
        executor=ExecutorStub(),
        strategy_factories={"mission": lambda _manifest, _command: CompleteStrategy()},
        verifier=verifier,
        evidence_collector=collector,
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
        activity_recorder=activity,
    )

    await controller.execute_command(_command())

    assert collector.called is True
    assert verifier.received["technology_evidence"] == ("technology:stone-age",)
    assert activity.phases == ["observing", "checking"]


async def test_controller_refreshes_canonical_budget_through_mission_fallback() -> None:
    from animetta.tools.minecraft.survival.mainline import build_nether_portal_mission
    from animetta.tools.minecraft.survival.registry import WorkflowRegistry
    from animetta.tools.minecraft.survival.workflows import nether_preparation_workflows
    from animetta.tools.minecraft.voyager.strategies.fallback import FallbackStrategy
    from animetta.tools.minecraft.voyager.strategies.mission import MissionStrategy

    mission = build_nether_portal_mission(mission_id="budget-context")
    registry = WorkflowRegistry()
    registry.register(
        next(w for w in nether_preparation_workflows() if w.target == "nether_iron_kit")
    )
    strategy = MissionStrategy(live=None, learn=None, fallback=FallbackStrategy(registry=registry))
    observation = Observation.model_validate(MESSAGES["Observation"]).model_copy(
        update={"inventory": {"stone_pickaxe": 1, "oak_planks": 23, "raw_iron": 0}}
    )

    class OreRuntime(RuntimeStub):
        async def observe(self, request):
            return observation

    class BudgetExecutor(ExecutorStub):
        def __init__(self):
            self.calls = []

        async def execute_step(self, **kwargs):
            self.calls.append(kwargs)
            if len(self.calls) == 2:
                raise ExecutorError(
                    ControlPlaneError(
                        code="TEST_STOP",
                        message="End controlled budget transfer test",
                        phase="admission",
                        outcome_known=True,
                        world_may_have_changed=False,
                        caller_may_resubmit=False,
                        operator_action="none",
                    )
                )
            account = (
                kwargs["account"]
                .reserve("first-ore", kwargs["step"].maximum_cost)
                .settle("first-ore", BudgetUsage(max_actions=1, max_blocks_changed=89))
            )
            return StepExecutionResult(
                receipt=ActionReceipt.model_validate(MESSAGES["ActionReceipt"]),
                after=observation.model_copy(
                    update={"inventory": {**observation.inventory, "raw_iron": 1}}
                ),
                account=account,
            )

    executor = BudgetExecutor()
    controller = UnifiedVoyagerController(
        runtime=OreRuntime(),
        repository=object(),
        executor=executor,
        strategy_factories={"mission": lambda _manifest, _command: strategy},
        verifier=VerifierStub(),
        evidence_collector=EvidenceCollectorStub(),
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
    )
    cmd = _command().model_copy(
        update={
            "payload": {
                "goal": mission.objectives[0].goal.model_dump(mode="json"),
                "execution_policy": {"stop_on_action_failure": True},
            },
            "effective_budget": mission.budget.model_copy(
                update=mission.objectives[0].budget.model_dump()
            ).model_dump(mode="json"),
        }
    )
    with pytest.raises(CommandExecutionError, match="End controlled budget transfer test"):
        await controller.execute_command(cmd)
    assert len(executor.calls) == 2
    assert executor.calls[0]["account"].used.max_blocks_changed == 0
    assert executor.calls[0]["step"].maximum_cost.max_blocks_changed == 192
    assert executor.calls[1]["account"].used.max_blocks_changed == 89
    assert executor.calls[1]["account"].remaining.max_blocks_changed == 167
    assert executor.calls[1]["step"].maximum_cost.max_blocks_changed == 146
    assert executor.calls[1]["account"].limit == executor.calls[0]["account"].limit


@pytest.mark.parametrize("error_code", ["PARTIAL_COLLECT", "BUDGET_EXHAUSTED"])
@pytest.mark.parametrize("recoverable", [True, False])
@pytest.mark.parametrize("stop_on_action_failure", [False, True])
async def test_controller_only_resumes_partial_collection_with_strategy_progress(
    recoverable: bool,
    error_code: str,
    stop_on_action_failure: bool,
) -> None:
    class PartialStrategy(CompleteStrategy):
        def propose(self, state, observation):
            if observation.inventory.get("oak_log", 0) >= 8:
                return super().propose(state, observation)
            return ExecuteStep(
                capability="collect",
                parameters={"count": 8 - observation.inventory.get("oak_log", 0)},
                maximum_cost=BudgetUsage(max_actions=1),
            )

        def accept_partial_result(self, state, before, after):
            assert before.inventory == {"oak_log": 1}
            assert after.inventory == {"oak_log": 4}
            return state if recoverable else None

        def accept_result(self, state, result):
            assert result["outcome"] == "success"
            return state

    class PartialExecutor(ExecutorStub):
        def __init__(self):
            self.calls = []

        async def execute_step(self, **kwargs):
            self.calls.append(kwargs)
            first = len(self.calls) == 1
            receipt = ActionReceipt.model_validate(MESSAGES["ActionReceipt"]).model_copy(
                update={"outcome": ReceiptOutcome.ERROR if first else ReceiptOutcome.SUCCESS}
            )
            account = BudgetAccount(
                limit=kwargs["account"].limit,
                used=BudgetUsage(max_actions=len(self.calls)),
            )
            result = StepExecutionResult(
                receipt=receipt,
                after=kwargs["before"].model_copy(
                    update={"inventory": {"oak_log": 4 if first else 8}}
                ),
                account=account,
            )
            if first:
                raise ExecutorError(
                    ControlPlaneError(
                        code=error_code,
                        message="4/8 collected",
                        phase="execution",
                        outcome_known=True,
                        world_may_have_changed=True,
                        caller_may_resubmit=False,
                        operator_action="inspect receipt",
                    ),
                    settled_result=result,
                )
            return result

    executor = PartialExecutor()
    verifier = VerifierStub()
    controller = UnifiedVoyagerController(
        runtime=RuntimeStub(),
        repository=object(),
        executor=executor,
        strategy_factories={"mission": lambda _manifest, _command: PartialStrategy()},
        verifier=verifier,
        evidence_collector=EvidenceCollectorStub(),
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
    )
    cmd = _command()
    cmd = cmd.model_copy(
        update={
            "payload": {
                **cmd.payload,
                **(
                    {"execution_policy": {"stop_on_action_failure": True}}
                    if stop_on_action_failure
                    else {}
                ),
            },
            "effective_budget": {
                **cmd.effective_budget,
                "max_actions": 3,
            },
        }
    )
    if not recoverable or stop_on_action_failure:
        with pytest.raises(CommandExecutionError, match="4/8 collected"):
            await controller.execute_command(cmd)
        assert len(executor.calls) == 1
        return

    await controller.execute_command(cmd)
    assert [call["step"].parameters["count"] for call in executor.calls] == [7, 4]
    assert executor.calls[1]["account"].used.max_actions == 1
    assert executor.calls[1]["previous_receipt_hash"]
    assert len(verifier.received["receipts"]) == 2


@pytest.mark.parametrize(
    "mode",
    [
        "recover",
        "strict",
        "unknown",
        "unreconciled",
        "unstable",
        "moving",
        "declined",
        "unhandled",
        "exhausted",
    ],
)
async def test_known_failure_recovery_preserves_account_deadline_and_receipt_chain(
    mode: str,
) -> None:
    class RecoveringStrategy(CompleteStrategy):
        recovery_calls = 0

        def propose(self, state, observation):
            if state.get("done"):
                return super().propose(state, observation)
            return ExecuteStep(
                capability="goto" if state.get("recovered") else "collect",
                parameters={"x": 0, "y": 64, "z": 0} if state.get("recovered") else {"count": 1},
                maximum_cost=BudgetUsage(max_actions=1),
            )

        def recover_failed_step(self, state, failed_step, before, after):
            self.recovery_calls += 1
            assert failed_step.capability == "collect"
            assert state["budget_remaining"].max_actions == (0 if mode == "exhausted" else 1)
            return {**state, "recovered": True} if mode not in {"declined", "exhausted"} else None

        def accept_result(self, state, result):
            assert result["outcome"] == "success"
            return {**state, "done": True}

    class RecoveringExecutor(ExecutorStub):
        def __init__(self):
            self.calls = []

        async def execute_step(self, **kwargs):
            self.calls.append(kwargs)
            first = len(self.calls) == 1
            receipt = ActionReceipt.model_validate(MESSAGES["ActionReceipt"])
            receipt = receipt.model_copy(
                update={
                    "outcome": ReceiptOutcome.ERROR if first else ReceiptOutcome.SUCCESS,
                    **(
                        {"reconciliation": type(receipt.reconciliation)("pending")}
                        if mode == "unreconciled"
                        else {}
                    ),
                    **(
                        {"post_observation": type(receipt.post_observation)("unstable")}
                        if mode == "unstable"
                        else {}
                    ),
                }
            )
            after = kwargs["before"]
            if mode == "moving":
                after = after.model_copy(
                    update={
                        "environment": {
                            **after.environment,
                            "on_ground": False,
                            "velocity": {"x": 0, "y": -0.1, "z": 0},
                        }
                    }
                )
            result = StepExecutionResult(
                receipt=receipt,
                after=after,
                account=kwargs["account"].charge(BudgetUsage(max_actions=1)),
            )
            if first:
                raise ExecutorError(
                    ControlPlaneError(
                        code="RUNTIME_DISCONNECTED" if mode == "unhandled" else "UNSAFE_AREA",
                        message="known action stopped",
                        phase="execution",
                        outcome_known=mode != "unknown",
                        world_may_have_changed=True,
                        caller_may_resubmit=False,
                        operator_action="inspect receipt",
                    ),
                    settled_result=result,
                )
            return result

    executor, strategy, verifier = RecoveringExecutor(), RecoveringStrategy(), VerifierStub()
    activity = ActivityRecorderStub()
    controller = UnifiedVoyagerController(
        runtime=RuntimeStub(),
        repository=object(),
        executor=executor,
        strategy_factories={"mission": lambda _manifest, _command: strategy},
        verifier=verifier,
        evidence_collector=EvidenceCollectorStub(),
        activity_recorder=activity,
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
    )
    cmd = _command()
    cmd = cmd.model_copy(
        update={
            "payload": {
                **cmd.payload,
                "execution_policy": {"stop_on_action_failure": mode == "strict"},
            },
            "effective_budget": {
                **cmd.effective_budget,
                "max_actions": 1 if mode == "exhausted" else 2,
            },
        }
    )
    if mode != "recover":
        with pytest.raises(ExecutorError, match="known action stopped"):
            await controller._execute_active(cmd)
        assert len(executor.calls) == 1
        assert strategy.recovery_calls == int(mode in {"declined", "exhausted"})
        return
    await controller._execute_active(cmd)
    assert [call["step"].capability for call in executor.calls] == ["collect", "goto"]
    assert [call["ordinal"] for call in executor.calls] == [1, 2]
    assert executor.calls[1]["account"].used.max_actions == 1
    assert all(call["command"] is cmd for call in executor.calls)
    assert (
        executor.calls[1]["previous_receipt_hash"] == verifier.received["receipts"][0].content_hash
    )
    assert len(verifier.received["receipts"]) == 2
    assert activity.phases == ["observing", "recovering", "checking"]


async def test_goal_verification_failure_retains_auditable_evidence() -> None:
    class FailingVerifier:
        def verify(self, **_kwargs):
            return {
                "satisfied": False,
                "predicate_results": [
                    {
                        "kind": "health_at_least",
                        "satisfied": False,
                        "evidence_hash": "e" * 64,
                    }
                ],
                "evidence_hashes": ["e" * 64],
            }

    controller = UnifiedVoyagerController(
        runtime=RuntimeStub(),
        repository=object(),
        executor=ExecutorStub(),
        strategy_factories={"mission": lambda _manifest, _command: CompleteStrategy()},
        verifier=FailingVerifier(),
        evidence_collector=EvidenceCollectorStub(),
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
    )

    with pytest.raises(CommandExecutionError) as caught:
        await controller.execute_command(_command())

    error = caught.value
    assert error.reason_code == "GOAL_VERIFICATION_FAILED"
    assert error.details["verification"]["predicate_results"][0]["satisfied"] is False
    assert error.terminal_result is not None
    assert error.terminal_result["error"]["code"] == "GOAL_VERIFICATION_FAILED"
    assert error.terminal_result["output"]["goal_evidence"]["technology_evidence"] == [
        "technology:stone-age"
    ]


async def test_blocked_unknown_retains_reconciliation_quarantine_evidence() -> None:
    receipt = ActionReceipt.model_validate(MESSAGES["ActionReceipt"])
    recovery_details = {
        "mutations_explained": False,
        "observable_state_diff": {
            "inventory": {
                "receipt_after": {"oak_log": 1},
                "fresh_observation": {"oak_log": 2},
            }
        },
    }

    class UnknownExecutor(ExecutorStub):
        async def reconcile_unknown(self, **_kwargs):
            return ReconciliationResult(
                RecoveryDecision.BLOCKED_UNKNOWN,
                recovery_details,
                receipt=receipt,
            )

    activity = ActivityRecorderStub()
    controller = UnifiedVoyagerController(
        runtime=RuntimeStub(),
        repository=object(),
        executor=UnknownExecutor(),
        strategy_factories={"mission": lambda _manifest, _command: CompleteStrategy()},
        verifier=VerifierStub(),
        evidence_collector=EvidenceCollectorStub(),
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
        activity_recorder=activity,
    )

    async def fail_with_unknown(_command):
        raise ExecutorError(
            ControlPlaneError(
                code="RUNTIME_RESPONSE_LOST",
                message="response lost after possible mutation",
                phase="recovery",
                outcome_known=False,
                world_may_have_changed=True,
                caller_may_resubmit=False,
                operator_action="inspect quarantined evidence",
            )
        )

    controller._execute_active = fail_with_unknown

    with pytest.raises(CommandExecutionError) as caught:
        await controller.execute_command(_command())

    error = caught.value
    assert error.terminal_state is CommandState.BLOCKED_UNKNOWN
    assert error.terminal_result is not None
    assert error.terminal_result["receipt_ids"] == [receipt.receipt_id]
    assert error.terminal_result["output"]["reconciliation"] == recovery_details
    assert error.terminal_result["error"]["details"] == recovery_details
    assert activity.phases == ["recovering"]


async def test_runtime_collector_inspects_the_exact_compiled_blueprint_region() -> None:
    runtime = RuntimeStub()
    requests = []

    async def inspect_region(request):
        requests.append(request)
        payload = {
            "schema_version": "2",
            "inspection_id": "inspection-1",
            "correlation_id": request.correlation_id,
            "runtime_instance_id": runtime.runtime_instance_id,
            "world_identity": runtime.observation.world_identity.model_dump(mode="json"),
            "captured_at_ms": 11,
            "tick": 11,
            "observation_id": runtime.observation.observation_id,
            "observation_hash": runtime.observation.content_hash,
            "bounds": request.bounds.model_dump(mode="json"),
            "blocks": {},
            "content_hash": "b" * 64,
        }
        from animetta.tools.gamebot.contracts.v2 import RegionInspection

        return RegionInspection.model_validate(payload)

    runtime.inspect_region = inspect_region
    compiled = BlueprintCompiler().compile(
        starter_shelter_blueprint(),
        BlueprintBinding(origin=(4, 65, 4), materials={}),
    )
    collector = RuntimeGoalEvidenceCollector(
        runtime=runtime,
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
    )

    evidence = await collector.collect(
        command=_command(),
        manifest=runtime.manifest,
        goal=_goal(),
        initial=runtime.observation,
        final=runtime.observation,
        receipts=(),
        output={"compiled_blueprints": (compiled,)},
    )

    assert len(requests) == 1
    assert requests[0].bounds == compiled.bounds
    assert requests[0].maximum_volume == compiled.bounds.volume
    assert evidence.region_inspections[0].bounds == compiled.bounds


async def test_runtime_collector_commits_discovery_only_after_goal_verification() -> None:
    runtime = RuntimeStub()
    store = InMemoryWorldFactStore()
    await store.connect()
    collector = RuntimeGoalEvidenceCollector(
        runtime=runtime,
        make_id=lambda prefix: f"{prefix}-id",
        now_ms=lambda: 10,
        discovery_projector=RuntimeDiscoveryProjector(store=store),
        world_fact_store=store,
    )
    initial = runtime.observation.model_copy(update={"inventory": {}})
    final_payload = runtime.observation.model_dump(mode="json")
    final_payload["inventory"] = {"raw_copper": 1}
    final_payload["visible_blocks"] = [
        {
            "block_id": "minecraft:copper_ore",
            "position": {"x": 20, "y": 63, "z": 20},
        }
    ]
    final = Observation.model_validate(final_payload)
    receipt = ActionReceipt.model_validate(MESSAGES["ActionReceipt"]).model_copy(
        update={
            "command_id": _command().command_id,
            "explained_mutations": (
                ActionReceipt.model_validate(MESSAGES["ActionReceipt"])
                .explained_mutations[0]
                .model_copy(update={"subject": "raw_copper", "delta": 1}),
            ),
        }
    )
    acquire = TypeAdapter(GoalSpec).validate_python(
        {
            "intent": "acquire",
            "target": "minecraft:raw_copper",
            "constraints": {"source_block": "minecraft:copper_ore"},
            "success_predicates": [
                {
                    "kind": "inventory_at_least",
                    "item": "minecraft:raw_copper",
                    "quantity": 1,
                }
            ],
        }
    )

    await collector.collect(
        command=_command(),
        manifest=runtime.manifest,
        goal=acquire,
        initial=initial,
        final=final,
        receipts=(receipt,),
        output={"selected_strategy": "learn"},
    )
    before = await store.list_scope(
        world_identity_hash=final.profile.world_identity_hash,
        environment_fingerprint=collector.environment_fingerprint(_command().command_id),
    )
    committed = await collector.commit_goal(_command().command_id, fallback_only=False)
    after = await store.list_scope(
        world_identity_hash=final.profile.world_identity_hash,
        environment_fingerprint=collector.environment_fingerprint(_command().command_id),
        state=WorldFactState.ACQUIRED,
    )

    assert before == ()
    assert {fact.identity.fact_key for fact in committed.observed} >= {
        "minecraft:copper_ore",
        "minecraft:raw_copper",
    }
    assert [fact.identity.fact_key for fact in after] == ["minecraft:raw_copper"]
    assert collector.record(_command().command_id).committed is True
