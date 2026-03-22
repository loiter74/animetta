"""工具执行节点"""

from typing import Dict, Any, List, Optional
from loguru import logger
from langchain_core.messages import ToolMessage
import json

from ..state import AgentState


async def tool_node(
    state: AgentState,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    工具执行节点

    输入: state["tool_calls"]
    输出: state["tool_results"], state["messages"]
    """
    session_id = state.get("session_id", "unknown")
    tool_calls = state.get("tool_calls")

    if not tool_calls:
        logger.debug(f"[{session_id}] [工具节点] 无工具调用")
        return {"tool_results": [], "tool_calls": None}

    logger.info(f"[{session_id}] [工具节点] 执行 {len(tool_calls)} 个工具调用")

    if config is None:
        config = state.get("_config", {})

    tools_map = (config if config else {}).get("configurable", {}).get("tools_map", {})

    if not tools_map:
        logger.error(f"[{session_id}] [工具节点] tools_map 未配置")
        return {"tool_results": [], "tool_calls": None, "error": "工具映射未配置"}

    tool_messages = []
    tool_results = []

    for tool_call in tool_calls:
        tool_id = tool_call.get("id", "unknown")
        tool_name = tool_call.get("name", "unknown")
        tool_args = tool_call.get("args", {})

        logger.info(f"[{session_id}] [工具节点] 调用工具: {tool_name}({tool_args})")

        try:
            tool_fn = tools_map.get(tool_name)

            if not tool_fn:
                error_msg = f"工具未找到: {tool_name}"
                logger.error(f"[{session_id}] [工具节点] {error_msg}")
                tool_messages.append(ToolMessage(content=f"错误: {error_msg}", tool_call_id=tool_id))
                tool_results.append({"error": error_msg})
                continue

            # 执行工具
            if hasattr(tool_fn, 'ainvoke'):
                result = await tool_fn.ainvoke(tool_args)
            elif hasattr(tool_fn, '_run'):
                result = tool_fn._run(**tool_args)
            else:
                import inspect
                if inspect.iscoroutinefunction(tool_fn):
                    result = await tool_fn(**tool_args)
                else:
                    result = tool_fn(**tool_args)

            result_str = _format_tool_result(result)
            logger.info(f"[{session_id}] [工具节点] {tool_name} 结果: {result_str[:100]}...")

            tool_messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))
            tool_results.append({"tool": tool_name, "args": tool_args, "result": result})

        except Exception as e:
            error_msg = f"工具执行错误: {str(e)}"
            logger.error(f"[{session_id}] [工具节点] {tool_name} 执行失败: {e}")
            tool_messages.append(ToolMessage(content=f"错误: {error_msg}", tool_call_id=tool_id))
            tool_results.append({"tool": tool_name, "args": tool_args, "error": str(e)})

    logger.info(f"[{session_id}] [工具节点] 完成 {len(tool_calls)} 个工具调用")

    return {
        "messages": tool_messages,
        "tool_results": tool_results,
        "tool_calls": None,
    }


def _format_tool_result(result: Any) -> str:
    """格式化工具执行结果"""
    if result is None:
        return "（无返回值）"
    if isinstance(result, str):
        return result
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            return str(result)
    return str(result)
