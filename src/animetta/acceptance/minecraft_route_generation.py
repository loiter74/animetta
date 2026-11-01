"""A two-proposal LangGraph for route drafts, with no runtime execution owner."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from animetta.tools.gamebot.contracts.v2 import RuntimeManifest
from animetta.tools.minecraft.mission.models import MissionSpec

from .minecraft_learning import MAX_MODEL_PROPOSALS
from .minecraft_route_planning import RouteDraft, RoutePlanningError, compile_route_draft


class RouteAttempt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    proposal: int
    raw_response: str
    issues: tuple[dict[str, Any], ...]
    usage: dict[str, Any] | None = None


class RouteGenerationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    mission: MissionSpec | None
    attempts: tuple[RouteAttempt, ...]


class _GenerationState(TypedDict):
    messages: list[dict[str, str]]
    attempts: list[RouteAttempt]
    raw_response: str
    usage: dict[str, Any] | None
    request_error: str | None
    mission: MissionSpec | None


async def generate_route_plan(
    *,
    invoke: Callable[[list[dict[str, str]]], Awaitable[dict[str, Any]]],
    messages: list[dict[str, str]],
    mission_id: str,
    home: tuple[float, float, float],
    origin: tuple[int, int, int],
    manifest: RuntimeManifest,
    initial_inventory: dict[str, int],
    max_proposals: int = MAX_MODEL_PROPOSALS,
    on_attempt: Callable[[RouteAttempt], None] | None = None,
    validate_mission: Callable[[MissionSpec], None] | None = None,
) -> RouteGenerationResult:
    """Keep route generation and correction in the same original proposal account."""
    if not 1 <= max_proposals <= MAX_MODEL_PROPOSALS:
        raise ValueError("route proposal limit must remain within the original two proposals")

    async def propose(state: _GenerationState) -> dict:
        try:
            response = await invoke(state["messages"])
            return {
                "raw_response": response.get("content", ""),
                "usage": response.get("usage"),
                "request_error": None,
            }
        except Exception as exc:
            # A failed provider request still consumes this proposal; it never
            # becomes a free retry or a new Minecraft submission.
            return {"raw_response": "", "usage": None, "request_error": type(exc).__name__}

    def validate(state: _GenerationState) -> dict:
        issues: tuple[dict[str, Any], ...] = ()
        mission = None
        try:
            if state["request_error"] is not None:
                raise ValueError(f"MODEL_REQUEST_FAILED:{state['request_error']}")
            draft = RouteDraft.model_validate_json(state["raw_response"])
            mission = compile_route_draft(
                draft,
                mission_id=mission_id,
                home=home,
                origin=origin,
                manifest=manifest,
                initial_inventory=initial_inventory,
            )
            if validate_mission is not None:
                validate_mission(mission)
        except RoutePlanningError as exc:
            issues = exc.issues
        except ValueError as exc:
            issues = ({"code": "ROUTE_DRAFT_INVALID", "message": str(exc)},)
        if issues:
            mission = None
        attempt = RouteAttempt(
            proposal=len(state["attempts"]) + 1,
            raw_response=state["raw_response"],
            issues=issues,
            usage=state["usage"],
        )
        if on_attempt is not None:
            on_attempt(attempt)
        history = list(state["messages"])
        if state["raw_response"]:
            history.append({"role": "assistant", "content": state["raw_response"]})
        if issues:
            history.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "issues": issues,
                            "remaining_proposals": max_proposals - attempt.proposal,
                            "instruction": "修正这些问题，只输出简短 RouteDraft JSON；主机任务、预算上限和蓝图不变。",
                        },
                        ensure_ascii=False,
                    ),
                }
            )
        return {"attempts": [*state["attempts"], attempt], "mission": mission, "messages": history}

    def next_node(state: _GenerationState) -> str:
        return (
            "finish"
            if state["mission"] is not None or len(state["attempts"]) >= max_proposals
            else "repair"
        )

    graph = StateGraph(_GenerationState)
    graph.add_node("propose", propose)
    graph.add_node("validate", validate)
    graph.add_edge(START, "propose")
    graph.add_edge("propose", "validate")
    graph.add_conditional_edges("validate", next_node, {"finish": END, "repair": "propose"})
    result = await graph.compile().ainvoke(
        {
            "messages": messages,
            "attempts": [],
            "raw_response": "",
            "usage": None,
            "request_error": None,
            "mission": None,
        }
    )
    return RouteGenerationResult(mission=result["mission"], attempts=tuple(result["attempts"]))
