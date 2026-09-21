"""Private exploration graph; checkpointed interrupts own every wait."""

from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, StateGraph
from langgraph.types import interrupt

from animetta.services.earth import EarthError
from animetta.tools.earth import get_earth_tools


class EarthGraphState(TypedDict):
    snapshot: dict[str, Any]
    event: dict[str, Any]


async def apply_event(state: EarthGraphState, config: RunnableConfig) -> dict[str, Any]:
    service = config["configurable"]["earth_service"]
    tools = {tool.name: tool for tool in get_earth_tools()}

    def bind(snapshot: dict[str, Any]) -> Any:
        capability = EarthCapability(service, snapshot, state["event"]["operation"])

        async def invoke(name: str, arguments: dict[str, Any]) -> Any:
            return await tools[name].ainvoke(
                arguments, config={"configurable": {"earth_capability": capability}}
            )

        return invoke

    return {"snapshot": await service.apply(state.get("snapshot", {}), state["event"], bind)}


class EarthCapability:
    """Bound to one graph transition, never persisted or shared with chat tools."""

    def __init__(self, service: Any, snapshot: dict[str, Any], operation: str) -> None:
        self.service, self.snapshot, self.operation = service, snapshot, operation

    async def search(self, query: str) -> list[dict[str, Any]]:
        if self.operation not in {"text", "audio"}:
            raise EarthError("EXPLICIT_QUERY_REQUIRED", "公共检索只接受用户主动查询。")
        return [candidate.model_dump() for candidate in await self.service.search.search(query)]

    async def observe(self) -> dict[str, Any]:
        return {
            key: self.snapshot.get(key)
            for key in ("view", "view_revision", "selected", "capabilities")
        }

    async def navigate(self, candidate_id: str) -> dict[str, Any]:
        selected = self.snapshot.get("selected")
        if self.operation != "select" or not selected or selected["id"] != candidate_id:
            raise EarthError("USER_SELECTION_REQUIRED", "请先选择候选地点。")
        self.service.navigate(self.snapshot, selected)
        return {"action_id": self.snapshot["action_id"], "status": "submitted"}


def wait_for_event(state: EarthGraphState) -> dict[str, Any]:
    snapshot = state["snapshot"]
    event = interrupt(
        {"phase": snapshot["phase"], "feedback_deadline": snapshot.get("feedback_deadline")}
    )
    return {"event": event}


def build_earth_graph(checkpointer: Any) -> Any:
    graph = StateGraph(EarthGraphState)
    graph.add_node("apply", apply_event)
    graph.add_node("wait", wait_for_event)
    graph.add_edge(START, "apply")
    graph.add_edge("apply", "wait")
    graph.add_edge("wait", "apply")
    return graph.compile(checkpointer=checkpointer)
