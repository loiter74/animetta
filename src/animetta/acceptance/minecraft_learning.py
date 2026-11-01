"""Outcome-only portal authority for bounded model-generated learning."""

from __future__ import annotations

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.mission.models import AutonomyPolicy, MissionObjective, MissionSpec
from animetta.tools.minecraft.skill.candidate import SkillCandidate, compile_candidate
from animetta.tools.minecraft.survival.mainline import build_nether_portal_mission
from animetta.tools.minecraft.voyager.budget import BudgetUsage
from animetta.tools.minecraft.voyager.strategies.learn import LearnStrategy

CONTRACT_ID = "bounded_learning_portal_v1"
MAX_MODEL_PROPOSALS = 2


def build_bounded_learning_portal_mission(
    *, mission_id: str, home: tuple[float, float, float], origin: tuple[int, int, int]
) -> MissionSpec:
    """Redistribute the original full-run account to one independently verified goal."""
    previous = build_nether_portal_mission(mission_id=mission_id, home=home)
    constraints = {f"home_{axis}": value for axis, value in zip("xyz", home, strict=True)}
    constraints.update({f"frame_x{i}": origin[0] + i for i in range(4)})
    constraints.update({f"frame_y{i}": origin[1] + i for i in range(5)})
    constraints["frame_z"] = origin[2]
    usage = BudgetUsage.model_validate(
        previous.budget.model_dump(
            exclude={
                "queue_timeout_ms",
                "execution_timeout_ms",
                "protected_items",
            }
        )
    )
    return MissionSpec(
        mission_id=mission_id,
        objectives=(
            MissionObjective(
                objective_id="portal",
                budget=usage,
                goal=previous.objectives[-1].goal.model_copy(update={"constraints": constraints}),
            ),
        ),
        budget=previous.budget,
        execution=previous.execution.model_copy(update={"allow_skill_learning": True}),
        autonomy=AutonomyPolicy(
            mode="bounded",
            allowed_domains=frozenset({"skill", "technology", "recovery"}),
            max_child_goals=previous.budget.max_strategy_attempts,
            max_new_skills=1,
            max_duration_ms=previous.budget.execution_timeout_ms,
            max_travel_distance=previous.budget.max_travel_distance,
            max_damage_taken=previous.budget.max_damage_taken,
            max_blocks_changed=previous.budget.max_blocks_changed,
            max_risk="destructive",
            stop_conditions=frozenset(
                {"mission_complete", "budget_exhausted", "user_stop", "unknown_world_state"}
            ),
        ),
    )


def validate_learning_mission(
    mission: MissionSpec, *, reference: MissionSpec, manifest: RuntimeManifest
) -> str:
    """Only the typed program may vary; budgets and the physical endpoint are immutable."""
    payload = mission.canonical_payload()
    if len(mission.objectives) != 1:
        raise ValueError("LEARNING_CONTRACT_REQUIRES_ONE_PORTAL_GOAL")
    constraints = payload["objectives"][0]["goal"]["constraints"]
    candidate = SkillCandidate.model_validate(constraints.pop("skill_candidate", None))
    if payload != reference.canonical_payload():
        raise ValueError("LEARNING_CONTRACT_AUTHORITY_CHANGED")
    revision, _ = compile_candidate(
        candidate,
        manifest=manifest,
        budget=mission.budget,
        goal=mission.objectives[0].goal,
        source_command_id="preflight-only",
    )
    return revision.revision_hash


def learning_first_decision(
    *, mission: MissionSpec, observation: Observation, manifest: RuntimeManifest
) -> dict:
    """Inspect the real candidate without a runtime call or a trusted-skill shortcut."""
    strategy = LearnStrategy(
        resolve_frontier=lambda _: (),
        propose_node=lambda _: {},
        max_frontier_nodes=1,
        max_attempts=MAX_MODEL_PROPOSALS,
        manifest=manifest,
        compilation_budget=mission.budget,
        source_command_id="preflight-only",
    )
    goal = mission.objectives[0].goal
    decision = strategy.propose(strategy.prepare(goal), observation)
    if decision.kind != "execute":
        raise ValueError(f"CANDIDATE_FIRST_DECISION_REJECTED: {decision}")
    return {
        "objective_id": "portal",
        "goal": goal.model_dump(mode="json"),
        "workflow_id": "model-generated-ir",
        "decision": decision.model_dump(mode="json"),
        "pure_read_only": True,
    }
