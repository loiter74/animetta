"""LLM 推理节点 - 支持工具调用和流式输出"""

from typing import Dict, Any, List, Optional, Any
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from .state import AgentState
from .config_store import get_service_context, get_config_value
from .interrupt_handler import get_interrupt_handler


async def llm_node(
    state: AgentState,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    LLM 推理节点

    输入: state["user_text"], state["messages"], state["persona"]
    输出: state["messages"], state["response_text"], state["response_chunks"], state["tool_calls"]
    """
    session_id = state.get("session_id", "unknown")
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLM节点] 开始处理...")

    # 验证输入
    if not user_text:
        logger.warning(f"[{session_id}] [LLM节点] 无用户文本，跳过")
        return {"error": "无用户文本", "response_text": "", "response_chunks": [], "tool_calls": None}

    service_context = get_service_context(session_id)
    if not service_context:
        logger.error(f"[{session_id}] [LLM节点] service_context 未配置")
        return {"error": "service_context 未配置", "response_text": "", "response_chunks": [], "tool_calls": None}

    llm_engine = service_context.llm_engine
    if not llm_engine:
        logger.error(f"[{session_id}] [LLM节点] LLM 引擎未初始化")
        return {"error": "LLM 引擎未初始化", "response_text": "", "response_chunks": [], "tool_calls": None}

    # 检查是否启用工具
    enable_tools = get_config_value(session_id, "enable_tools", False)
    chat_model = get_config_value(session_id, "chat_model", None)

    if enable_tools and chat_model:
        return await _llm_with_tools(session_id, state, service_context, chat_model)
    else:
        return await _llm_without_tools(session_id, state, service_context)


async def _llm_with_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
    chat_model: Any,
) -> Dict[str, Any]:
    """使用工具调用模式"""
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))
    llm_engine = service_context.llm_engine

    logger.info(f"[{session_id}] [LLM节点] 使用工具调用模式")

    system_prompt = state.get("system_prompt")
    if not system_prompt and service_context.config:
        system_prompt = service_context.config.get_system_prompt()

    bound_tools = getattr(chat_model, "bound_tools", []) or getattr(chat_model, "tools", [])

    history_for_llm = [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))]

    try:
        response = await llm_engine.chat_with_tools(
            user_text,
            tools=bound_tools,
            langchain_history=history_for_llm,
            system_prompt=system_prompt,
        )

        if isinstance(response, dict):
            if response.get("tool_calls"):
                tool_calls = response["tool_calls"]
                formatted_tool_calls = [
                    {"id": tc.get("id", ""), "name": tc.get("name", ""), "args": tc.get("args", {})}
                    for tc in tool_calls
                ]

                ai_message = AIMessage(content=response.get("content", "") or "正在调用工具...", tool_calls=tool_calls)

                return {
                    "response_text": response.get("content", "") or "正在调用工具...",
                    "response_chunks": [response.get("content", "") or ""],
                    "messages": [ai_message],
                    "tool_calls": formatted_tool_calls,
                }
            else:
                full_response = response.get("content", "")
                logger.info(f"[{session_id}] [LLM节点] LLM 回复: {full_response[:100]}...")
                ai_message = AIMessage(content=full_response)

                return {
                    "response_text": full_response,
                    "response_chunks": [full_response],
                    "messages": [ai_message],
                    "tool_calls": None,
                }

    except Exception as e:
        logger.error(f"[{session_id}] [LLM节点] 工具调用失败: {e}")
        return await _llm_without_tools(session_id, state, service_context)


async def _llm_without_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
) -> Dict[str, Any]:
    """使用流式模式（无工具）"""
    user_text = state.get("user_text", "")
    llm_engine = service_context.llm_engine
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLM节点] 使用流式模式（无工具）")

    system_prompt = state.get("system_prompt", "")

    if not messages or not isinstance(messages[0], SystemMessage):
        if system_prompt:
            messages.insert(0, SystemMessage(content=system_prompt))

    user_id = state.get("user_id")
    user_name = state.get("user_name")

    if not messages or not isinstance(messages[-1], HumanMessage):
        content = f"[{user_name}]: {user_text}" if user_name else user_text
        messages.append(HumanMessage(content=content, name=user_id or "user"))

    interrupt_handler = get_interrupt_handler()
    interrupt_handler.clear_interrupt(session_id)

    chunks = []
    full_response = ""

    async for chunk in llm_engine.chat_stream(user_text, system_prompt=system_prompt):
        if interrupt_handler.is_interrupted(session_id):
            logger.warning(f"[{session_id}] [LLM节点] 检测到打断信号，停止生成")
            break
        chunks.append(chunk)
        full_response += chunk
        if len(chunks) % 10 == 0:
            logger.debug(f"[{session_id}] [LLM节点] 已接收 {len(chunks)} 个块...")

    logger.info(f"[{session_id}] [LLM节点] LLM 回复: {full_response[:100]}...")

    ai_message = AIMessage(content=full_response)

    return {
        "response_text": full_response,
        "response_chunks": chunks,
        "messages": [ai_message],
        "tool_calls": None,
        "metadata": {**state.get("metadata", {})},
    }
