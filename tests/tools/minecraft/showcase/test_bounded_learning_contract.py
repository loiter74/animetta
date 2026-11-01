"""The endpoint contract preserves budgets and never upgrades candidate proof."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from animetta.acceptance.minecraft_learning import (
    build_bounded_learning_portal_mission,
    learning_first_decision,
    validate_learning_mission,
)
from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.mission.models import MissionSpec
from animetta.tools.minecraft.survival.mainline import build_nether_portal_mission
from animetta.tools.minecraft.voyager.goal_verifier import GoalVerifier

MESSAGES = json.loads(
    (Path(__file__).resolve().parents[4] / "contracts/gamebot/v2/fixtures/golden.json").read_text(
        encoding="utf-8"
    )
)["messages"]


def reference():
    return build_bounded_learning_portal_mission(
        mission_id="learning-contract", home=(0, 64, 0), origin=(2, 64, 0)
    )


def candidate_payload():
    payload = reference().canonical_payload()
    payload["objectives"][0]["goal"]["constraints"]["skill_candidate"] = {
        "program": {
            "name": "test_candidate",
            "steps": [
                {
                    "kind": "action",
                    "step_id": "gather",
                    "capability": "collect",
                    "parameters": {"count": {"kind": "literal", "value": 1}},
                }
            ],
            "postconditions": [
                {
                    "op": "gte",
                    "left": {"kind": "observation", "path": "health"},
                    "right": {"kind": "literal", "value": 1},
                }
            ],
        }
    }
    return payload


def test_outcome_contract_redistributes_exact_original_caps_and_keeps_portal_proof():
    mission = reference()
    old = build_nether_portal_mission(mission_id=mission.mission_id, home=(0, 64, 0))
    assert mission.budget == old.budget
    assert mission.budget.max_actions == 117
    assert mission.budget.max_travel_distance == 1984
    assert mission.autonomy.max_new_skills == 1
    assert len(mission.objectives) == 1
    assert (
        mission.objectives[0].goal.success_predicates == old.objectives[-1].goal.success_predicates
    )
    assert mission.objectives[0].budget.max_blocks_changed == mission.budget.max_blocks_changed


def test_candidate_compiles_and_first_decision_does_not_prove_the_portal():
    manifest = RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"])
    mission = MissionSpec.model_validate(candidate_payload())
    assert len(validate_learning_mission(mission, reference=reference(), manifest=manifest)) == 64
    observation = Observation.model_validate(MESSAGES["Observation"])
    assert (
        learning_first_decision(mission=mission, observation=observation, manifest=manifest)[
            "decision"
        ]["capability"]
        == "collect"
    )
    verified = GoalVerifier().verify(
        goal=mission.objectives[0].goal, initial=observation, final=observation, receipts=[]
    )
    assert verified["satisfied"] is False


@pytest.mark.parametrize("change", ["budget", "endpoint", "location"])
def test_model_cannot_change_authority_or_site(change):
    payload = candidate_payload()
    if change == "budget":
        payload["budget"]["max_actions"] += 1
    elif change == "endpoint":
        payload["objectives"][0]["goal"]["success_predicates"] = [
            {"kind": "inventory_at_least", "item": "dirt", "quantity": 1}
        ]
    else:
        payload["objectives"][0]["goal"]["constraints"]["frame_x0"] += 10
    mission = MissionSpec.model_validate(payload)
    with pytest.raises(ValueError, match="AUTHORITY_CHANGED"):
        validate_learning_mission(
            mission,
            reference=reference(),
            manifest=RuntimeManifest.model_validate(MESSAGES["RuntimeManifest"]),
        )


def test_candidate_quota_is_checked_before_any_world_action():
    payload = candidate_payload()
    payload["autonomy"]["max_new_skills"] = 0
    with pytest.raises(ValidationError, match="learning quota"):
        MissionSpec.model_validate(payload)
    payload = candidate_payload()
    payload["execution"]["allow_skill_learning"] = False
    with pytest.raises(ValidationError, match="learning quota"):
        MissionSpec.model_validate(payload)
