"""Environment-trusted revision selection over the shared bounded IR interpreter."""

from __future__ import annotations

from animetta.tools.gamebot.contracts.v2 import Observation, RuntimeManifest
from animetta.tools.minecraft.skill.applicability import SkillApplicability
from animetta.tools.minecraft.skill.ir import SkillRevision
from animetta.tools.minecraft.skill.selection import (
    SkillSelectionCandidate,
    SkillSelectionContext,
    select_applicable_skill,
)
from animetta.tools.minecraft.skill.trust import (
    SkillEnvironmentTrust,
    stable_environment_fingerprint,
)

from ..goal_models import GoalSpec
from .base import StrategyDecision
from .program import SkillProgramStrategy


class LiveStrategy(SkillProgramStrategy):
    def __init__(
        self,
        *,
        revisions: dict[str, SkillRevision],
        applicabilities: dict[str, SkillApplicability],
        trusts: list[SkillEnvironmentTrust],
        manifest: RuntimeManifest,
        allow_skill_reuse: bool = True,
    ) -> None:
        super().__init__(manifest=manifest)
        self._revisions = revisions
        self._applicabilities = applicabilities
        self._trusts = trusts
        self._allow_skill_reuse = allow_skill_reuse

    def prepare(self, goal: GoalSpec | None) -> dict:
        state = super().prepare(goal)
        state["selection_pending"] = True
        return state

    def propose(self, state: dict, observation: Observation) -> StrategyDecision:
        if state.get("selection_pending"):
            self._select_revision(state, observation)
        return super().propose(state, observation)

    def _select_revision(self, state: dict, observation: Observation) -> None:
        environment = stable_environment_fingerprint(self._manifest.profile)
        trust_by_revision = {
            trust.revision_hash: trust
            for trust in self._trusts
            if trust.environment_fingerprint == environment
        }
        candidates = tuple(
            SkillSelectionCandidate(
                revision=revision,
                applicability=self._applicabilities[revision_hash],
                trust=trust_by_revision[revision_hash],
            )
            for revision_hash, revision in self._revisions.items()
            if revision_hash in self._applicabilities and revision_hash in trust_by_revision
        )
        constraints = state["goal"].constraints
        discovery_states = constraints.get("discovery_states", {})
        technology_nodes = constraints.get("technology_nodes", ())
        selection = select_applicable_skill(
            candidates,
            SkillSelectionContext(
                goal=state["goal"],
                environment_fingerprint=environment,
                available_capabilities=frozenset(
                    capability.name for capability in self._manifest.capabilities
                ),
                discovery_states=(discovery_states if isinstance(discovery_states, dict) else {}),
                technology_nodes=frozenset(
                    technology_nodes
                    if isinstance(technology_nodes, (list, tuple, set, frozenset))
                    else ()
                ),
                observation=observation.model_dump(mode="python"),
                allow_skill_reuse=self._allow_skill_reuse,
            ),
        )
        selected = (
            self._revisions.get(selection.selected_revision_hash)
            if selection.selected_revision_hash is not None
            else None
        )
        state["revision"] = selected
        state["frames"] = (
            ({"kind": "sequence", "steps": selected.program.steps, "index": 0},)
            if selected is not None
            else ()
        )
        state["bound_parameters"] = self._bound_defaults(selected, selection.bound_parameters)
        state["selection_exclusions"] = selection.exclusions
        state["selection_pending"] = False
