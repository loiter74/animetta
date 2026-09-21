"""Earth model tools; capability injection prevents global/private session leakage."""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from animetta.services.earth import EarthError


def _capability(config: RunnableConfig) -> Any:
    capability = config.get("configurable", {}).get("earth_capability")
    if capability is None:
        raise EarthError("EARTH_NOT_OPEN", "地球工具只能在当前私密探索会话中使用。")
    return capability


@tool
async def earth_search(query: str, config: RunnableConfig) -> list[dict[str, Any]]:
    """检索用户明确提出的地名，返回来源与候选，不移动镜头。"""
    return await _capability(config).search(query)


@tool
async def earth_observe(config: RunnableConfig) -> dict[str, Any]:
    """读取当前地球视图与用户确认的上下文；未授权时不读取图像。"""
    return await _capability(config).observe()


@tool
async def earth_navigate(candidate_id: str, config: RunnableConfig) -> dict[str, Any]:
    """向当前私密地图提交已选候选的导航，等待客户端回执确认完成。"""
    return await _capability(config).navigate(candidate_id)


earth_search.metadata = {"effect": "read_only", "tool_source": "builtin"}
earth_observe.metadata = {"effect": "read_only", "tool_source": "builtin"}
earth_navigate.metadata = {"effect": "state_changing", "tool_source": "builtin"}


def get_earth_tools() -> list[Any]:
    return [earth_search, earth_observe, earth_navigate]


__all__ = ["get_earth_tools"]
