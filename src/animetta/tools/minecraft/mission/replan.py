"""Bounded, perception-driven budget rebalancing for mission objectives.

When an objective fails because its static budget envelope is exhausted
(``BUDGET_EXHAUSTED``), the coordinator may consult a :class:`RebalancePlanner`
with dual-channel evidence — a structured :class:`ObservationDigest` built from
the runtime control plane (code perception) and a :class:`VisionDigest` built
from the dual-perception consensus (visual perception) — and retry the
objective once per allowed rebalance with a proposal-validated budget.

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


class RebalanceProposal(_FrozenModel):
    """A model (or rule) proposal for redistributing mission budget."""

    rationale: str = Field(max_length=1200)
    new_budget: BudgetUsage


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

    Hard constraints (all must hold):

    1. The failed objective must actually be exhausted on some dimension.
    2. The new envelope may never shrink any dimension, and must strictly grow
       at least one exhausted dimension — a rebalance that changes nothing is
       an infinite retry loop in disguise.
    """

    _validate_dimensions(proposal.new_budget, request.failed_objective.budget, request)
    return proposal.new_budget


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
    grew = False
    for dimension in _BUDGET_DIMENSIONS:
        old_limit = getattr(old_budget, dimension)
        new_limit = getattr(new_budget, dimension)
        if new_limit < old_limit:
            raise RebalanceValidationError(
                f"rebalance may not shrink dimension '{dimension}' of the failed objective"
            )
        if dimension in exhausted_dimensions and new_limit <= old_limit:
            raise RebalanceValidationError(f"rebalance must grow exhausted dimension '{dimension}'")
        if new_limit > old_limit:
            grew = True
    if not grew:
        raise RebalanceValidationError("rebalance must enlarge at least one budget dimension")


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
