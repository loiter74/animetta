"""
工具执行节点 (Phase 3)

负责：
1. 接收 LLM 请求的工具调用 (state["tool_calls"])
2. 执行工具调用
3. 将结果写入 state["tool_results"] 和 messages

Phase 3: 完整实现工具调用逻辑
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from langchain_core.messages import ToolMessage

from ..state import AgentState


async def tool_node(
    state: AgentState,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    工具执行节点

    输入: state["tool_calls"]
    输出: state["tool_results"], state["messages"] (追加工具结果消息)

    Phase 3: 完整实现工具调用逻辑

    Args:
        state: 当前状态
        config: LangGraph 传入的运行时配置（自动注入）

    Returns:
        状态更新字典
    """
    session_id = state.get("session_id", "unknown")
    tool_calls = state.get("tool_calls")

    # 如果没有工具调用，直接返回
    if not tool_calls:
        logger.debug(f"[{session_id}] [工具节点] 无工具调用")
        return {
            "tool_results": [],
            "tool_calls": None,
        }

    logger.info(f"[{session_id}] [工具节点] 执行 {len(tool_calls)} 个工具调用")

    # config 由 LangGraph 自动注入
    if config is None:
        config = state.get("_config", {})

    # 获取工具映射
    tools_map = (config if config else {}).get("configurable", {}).get("tools_map", {})

    if not tools_map:
        logger.error(f"[{session_id}] [工具节点] tools_map 未配置")
        return {
            "tool_results": [],
            "tool_calls": None,
            "error": "工具映射未配置",
        }

    # 执行工具调用
    tool_messages = []
    tool_results = []

    for tool_call in tool_calls:
        tool_id = tool_call.get("id", "unknown")
        tool_name = tool_call.get("name", "unknown")
        tool_args = tool_call.get("args", {})

        logger.info(f"[{session_id}] [工具节点] 调用工具: {tool_name}({tool_args})")

        try:
            # 查找工具
            tool_fn = tools_map.get(tool_name)

            if not tool_fn:
                error_msg = f"工具未找到: {tool_name}"
                logger.error(f"[{session_id}] [工具节点] {error_msg}")
                tool_messages.append(
                    ToolMessage(
                        content=f"错误: {error_msg}",
                        tool_call_id=tool_id,
                    )
                )
                tool_results.append({"error": error_msg})
                continue

            # 执行工具
            # 检查工具类型并调用相应方法
            import inspect

            # LangChain BaseTool 使用 ainvoke() 或 _run()
            if hasattr(tool_fn, 'ainvoke'):
                # LangChain StructuredTool
                try:
                    result = await tool_fn.ainvoke(tool_args)
                except Exception as e:
                    raise Exception(f"LangChain tool 调用失败: {e}")
            elif hasattr(tool_fn, '_run'):
                # LangChain 同步工具
                result = tool_fn._run(**tool_args)
            elif inspect.iscoroutinefunction(tool_fn):
                # 异步函数
                result = await tool_fn(**tool_args)
            else:
                # 普通函数
                result = tool_fn(**tool_args)

            # 格式化结果
            result_str = _format_tool_result(result)

            logger.info(f"[{session_id}] [工具节点] {tool_name} 结果: {result_str[:100]}...")

            tool_messages.append(
                ToolMessage(
                    content=result_str,
                    tool_call_id=tool_id,
                )
            )
            tool_results.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })

        except Exception as e:
            error_msg = f"工具执行错误: {str(e)}"
            logger.error(f"[{session_id}] [工具节点] {tool_name} 执行失败: {e}")
            tool_messages.append(
                ToolMessage(
                    content=f"错误: {error_msg}",
                    tool_call_id=tool_id,
                )
            )
            tool_results.append({
                "tool": tool_name,
                "args": tool_args,
                "error": str(e),
            })

    logger.info(f"[{session_id}] [工具节点] 完成 {len(tool_calls)} 个工具调用")

    return {
        "messages": tool_messages,
        "tool_results": tool_results,
        "tool_calls": None,  # 清除，避免再次进入工具节点
    }


def _format_tool_result(result: Any) -> str:
    """
    格式化工具执行结果

    Args:
        result: 工具执行结果

    Returns:
        str: 格式化后的字符串
    """
    if result is None:
        return "（无返回值）"

    if isinstance(result, str):
        return result

    if isinstance(result, (dict, list)):
        import json
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            return str(result)

    return str(result)
