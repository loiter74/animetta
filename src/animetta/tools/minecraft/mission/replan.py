"""Bounded, perception-driven tactical rebalancing for mission objectives.

When an objective fails, the coordinator may consult a
:class:`RebalancePlanner` with dual-channel evidence — a structured
:class:`ObservationDigest` built from the runtime control plane (code
perception) and a :class:`VisionDigest` built from the dual-perception
consensus (visual perception) — and retry the objective once per allowed
rebalance with a proposal-validated change. Two failure classes exist:

* Budget wall (``BUDGET_EXHAUSTED`` with a dimension at >=95%): the proposal
  must strictly grow at least one exhausted dimension and may not grow any
  non-exhausted dimension; shrinking any dimension is allowed so the retry can
  fund its growth from within the mission account.
* Deadline/tactic class (progress-but-slow navigation, e.g. the r114 gravel
  churn climb killed by the default segment timer, or a mislabelled envelope
  stop with every dimension far from exhausted): the proposal must set
  :attr:`RebalanceProposal.navigation_timeout_ms` and may not grow any budget
  dimension — a smaller, affordable retry envelope is fine, a bigger one is
  smuggled budget.

In both classes the retry envelope must fit the mission account's
``remaining_budget`` (settled after the failed attempt); the coordinator's
reserve enforces that arithmetic regardless of what validation accepts.

The product side owns the mechanism and hard constraints; the model dialogue
lives in the harness (:mod:`.zcode.mc-route-acceptance-v2.replan_planning`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from ...gamebot.contracts.v2.receipts import ActionReceipt
from ..voyager.budget import BudgetUsage
from .models import MissionObjective


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ObservationDigest(_FrozenModel):
    """Structured runtime facts (code perception) at the moment of failure."""

    position: tuple[float, float, float] | None = None
    health: float | None = None
    food: float | None = None
    inventory: dict[str, int] = Field(default_factory=dict)
    distance_travelled: float = Field(ge=0)
    blocks_changed: int = Field(ge=0)
    commands_issued: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)


class VisionDigest(_FrozenModel):
    """Adopted dual-perception consensus (visual perception) at failure.

    Mirrors :class:`~animetta.tools.minecraft.perception.models.PerceptionConsensus`
    — the product's adopted visual verdict. Rich scene narration belongs to the
    harness-side planner prompt, not to this durable record.
    """

    consensus_action: str = Field(pattern="^(continue|alert|halt)$")
    adopted_danger: str = Field(pattern="^(none|warning|critical)$")
    mode: str = Field(pattern="^(monitor|verify_completion)$")
    checked_at_ms: int = Field(ge=0)


@dataclass(frozen=True)
class RebalanceRequest:
    """Everything a planner needs to decide a budget redistribution."""

    mission_id: str
    failed_objective: MissionObjective
    remaining_objectives: tuple[MissionObjective, ...]
    observation_digest: ObservationDigest
    vision_digest: VisionDigest
    terminal_receipt: ActionReceipt
    failure_reason_code: str
    rebalances_used: int
    rebalances_allowed: int
    remaining_budget: BudgetUsage | None = None


class RebalanceProposal(_FrozenModel):
    """A model (or rule) proposal for changing one failed objective's retry.

    ``new_budget`` redistributes the envelope (budget-wall class);
    ``navigation_timeout_ms`` extends the per-goto-segment navigation deadline
    (deadline class, 15s-120s, mirroring the runtime's clamp).
    """

    rationale: str = Field(max_length=1200)
    new_budget: BudgetUsage
    navigation_timeout_ms: int | None = Field(default=None, ge=15_000, le=120_000)


@dataclass
class RebalanceWindow:
    """Per-mission accounting of how many rebalances have been spent."""

    used: int = 0
    reasons: tuple[str, ...] = field(default=())

    def allow(self, policy_limit: int) -> bool:
        return self.used < policy_limit


class RebalancePlanner(Protocol):
    async def plan_rebalance(self, request: RebalanceRequest) -> RebalanceProposal | None:
        """Return a validated proposal, or ``None`` to keep the failure terminal."""
        ...


class RebalanceValidationError(ValueError):
    """Raised when a proposal violates the hard constraints of the mechanism."""


def validate_rebalance(
    *,
    proposal: RebalanceProposal,
    request: RebalanceRequest,
) -> BudgetUsage:
    """Check a proposal against the mechanism's hard constraints.

    Budget-wall class (some dimension >=95% exhausted): the new envelope must
    strictly grow at least one exhausted dimension; non-exhausted dimensions
    may not grow (shrinking any dimension is allowed so the growth can be
    funded from within the mission account).

    Deadline class (nothing exhausted): the proposal must set
    ``navigation_timeout_ms`` and may not grow any budget dimension — smaller
    affordable envelopes are fine, larger ones are smuggled budget.

    Affordability (every dimension within ``request.remaining_budget`` when
    present) is checked here too so the planner gets an honest, specific
    rejection instead of a bare reserve failure.
    """

    if _exhausted_dimensions(request):
        _validate_dimensions(proposal.new_budget, request.failed_objective.budget, request)
    else:
        _validate_deadline_extension(proposal, request)
    _validate_affordable(proposal.new_budget, request)
    return proposal.new_budget


def _validate_affordable(new_budget: BudgetUsage, request: RebalanceRequest) -> None:
    remaining = getattr(request, "remaining_budget", None)
    if remaining is None:
        return
    for dimension in _BUDGET_DIMENSIONS:
        limit = getattr(remaining, dimension)
        if limit <= 0:
            continue
        if getattr(new_budget, dimension) > limit:
            raise RebalanceValidationError(
                f"rebalance exceeds the mission account's remaining '{dimension}' headroom ({limit})"
            )


def _validate_deadline_extension(
    proposal: RebalanceProposal,
    request: RebalanceRequest,
) -> None:
    if proposal.navigation_timeout_ms is None:
        raise RebalanceValidationError(
            "deadline-class rebalance requires navigation_timeout_ms (no dimension is exhausted)"
        )
    old_budget = request.failed_objective.budget
    for dimension in _BUDGET_DIMENSIONS:
        if getattr(proposal.new_budget, dimension) > getattr(old_budget, dimension):
            raise RebalanceValidationError(
                f"deadline-class rebalance may not grow dimension '{dimension}'"
            )


def _validate_dimensions(
    new_budget: BudgetUsage,
    old_budget: BudgetUsage,
    request: RebalanceRequest,
) -> None:
    exhausted_dimensions = _exhausted_dimensions(request)
    if not exhausted_dimensions:
        raise RebalanceValidationError(
            "rebalance requires an exhausted dimension in the failed objective"
        )
    grew_exhausted = False
    for dimension in _BUDGET_DIMENSIONS:
        old_limit = getattr(old_budget, dimension)
        new_limit = getattr(new_budget, dimension)
        if dimension not in exhausted_dimensions and new_limit > old_limit:
            raise RebalanceValidationError(
                f"rebalance may not grow non-exhausted dimension '{dimension}'"
            )
        if dimension in exhausted_dimensions and new_limit > old_limit:
            grew_exhausted = True
    if not grew_exhausted:
        raise RebalanceValidationError(
            "rebalance must strictly grow at least one exhausted dimension"
        )


_BUDGET_DIMENSIONS = (
    "max_actions",
    "max_strategy_attempts",
    "max_travel_distance",
    "max_blocks_changed",
    "max_damage_taken",
)


def _exhausted_dimensions(request: RebalanceRequest) -> tuple[str, ...]:
    usage = request.terminal_receipt.budget_usage
    exhausted: list[str] = []
    for dimension, used in (
        ("max_actions", usage.max_actions),
        ("max_travel_distance", usage.max_travel_distance),
        ("max_blocks_changed", usage.max_blocks_changed),
        ("max_damage_taken", usage.max_damage_taken),
    ):
        limit = getattr(request.failed_objective.budget, dimension)
        if limit > 0 and used >= limit * 0.95:
            exhausted.append(dimension)
    return tuple(exhausted)
