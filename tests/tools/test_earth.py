"""Registry and production tool policy for the private Earth capability."""

import pytest

from animetta.orchestration.graph.earth_graph import EarthCapability
from animetta.orchestration.graph.tool_execution_policy import ToolEffect, ToolExecutionPolicy
from animetta.services.earth import EarthError
from animetta.tools.base import load_tools_from_config


def test_registry_enabled_and_disabled_and_mutation_classification() -> None:
    tools, mapping = load_tools_from_config({"builtin_tools": [], "earth": {"enabled": True}})
    assert set(mapping) == {"earth_search", "earth_observe", "earth_navigate"}
    policy = ToolExecutionPolicy(production=True)
    for tool in tools:
        decision = policy.evaluate(tool.name, {}, tool)
        assert decision.effect == (
            ToolEffect.STATE_CHANGING if tool.name == "earth_navigate" else ToolEffect.READ_ONLY
        )
    assert load_tools_from_config({"builtin_tools": [], "earth": {"enabled": False}})[0] == []


async def test_auto_transition_cannot_query_public_provider_or_choose_place() -> None:
    capability = EarthCapability(None, {}, "tick")
    with pytest.raises(EarthError, match="主动查询"):
        await capability.search("Shanghai")
    with pytest.raises(EarthError, match="选择候选"):
        await capability.navigate("unknown")
