"""LLM 推理节点 - 支持工具调用和流式输出"""

from typing import Dict, Any, List, Optional
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.types import RunnableConfig

from .state import AgentState
from .interrupt_handler import get_interrupt_handler


# ========================================
# RAG 记忆检索辅助函数
# ========================================

def _get_memory_system(config: Optional[RunnableConfig]) -> Optional[Any]:
    """从 LangGraph config 获取 memory_system"""
    if config:
        service_context = config.get("configurable", {}).get("service_context")
        if service_context and hasattr(service_context, "memory_system"):
            return service_context.memory_system
    return None


def _format_memory_context(memory_turns: List[Any], max_items: int = 5) -> str:
    """
    格式化记忆上下文为文本

    Args:
        memory_turns: MemoryTurn 对象列表
        max_items: 最大显示条数

    Returns:
        格式化的记忆文本
    """
    if not memory_turns:
        return ""

    # 只取前 max_items 条
    selected = memory_turns[:max_items]

    lines = ["## 相关记忆"]
    for i, turn in enumerate(selected, 1):
        # 优先使用口语化版本（如果有）
        if hasattr(turn, "metadata"):
            oral = turn.metadata.get("oral_version")
        else:
            oral = None

        user_text = turn.user_input if hasattr(turn, "user_input") else ""
        agent_text = turn.agent_response if hasattr(turn, "agent_response") else ""

        if oral:
            lines.append(f"{i}. {oral}")
        else:
            # 兼容旧数据：没有口语化版本时使用原始文本
            if user_text and agent_text:
                lines.append(f"{i}. 你说过：{user_text}")
                lines.append(f"   我回复：{agent_text}")
            elif user_text:
                lines.append(f"{i}. 你说过：{user_text}")

    return "\n".join(lines) if len(lines) > 1 else ""


async def _retrieve_memory_context(
    session_id: str,
    query: str,
    config: Optional[RunnableConfig],
    max_turns: int = 5,
) -> str:
    """
    检索记忆上下文

    Args:
        session_id: 会话 ID
        query: 查询文本（用户输入）
        config: LangGraph config
        max_turns: 最大检索轮数

    Returns:
        格式化的记忆文本
    """
    memory_system = _get_memory_system(config)
    if not memory_system:
        logger.debug(f"[{session_id}] [LLM节点] MemorySystem 未配置，跳过 RAG")
        return ""

    try:
        memory_turns = await memory_system.retrieve_context(
            query=query,
            session_id=session_id,
            max_turns=max_turns,
        )

        if memory_turns:
            context = _format_memory_context(memory_turns, max_items=max_turns)
            logger.info(f"[{session_id}] [LLM节点] RAG 检索到 {len(memory_turns)} 条记忆")
            logger.debug(f"[{session_id}] [LLM节点] 记忆上下文: {context[:200]}...")
            return context
        else:
            logger.debug(f"[{session_id}] [LLM节点] RAG 未检索到相关记忆")
            return ""

    except Exception as e:
        logger.warning(f"[{session_id}] [LLM节点] RAG 检索失败: {e}")
        return ""


def _enrich_system_prompt(
    base_prompt: Optional[str],
    memory_context: str,
) -> str:
    """
    将记忆上下文注入到 system prompt

    Args:
        base_prompt: 基础 system prompt
        memory_context: 记忆上下文文本

    Returns:
        增强后的 system prompt
    """
    if not memory_context:
        return base_prompt or ""

    parts = []
    if base_prompt:
        parts.append(base_prompt)

    # 添加记忆上下文
    parts.append(memory_context)

    # 添加指令
    parts.append("\n请参考以上记忆，自然地回答用户的问题。如果记忆中没有相关信息，就正常回答。")

    return "\n\n---\n\n".join(parts)


def _get_service_context(config: Optional[RunnableConfig]) -> Optional[Any]:
    """从 LangGraph config 获取 service_context"""
    if config:
        return config.get("configurable", {}).get("service_context")
    return None


def _get_config_value(config: Optional[RunnableConfig], key: str, default: Any = None) -> Any:
    """从 LangGraph config 获取配置值"""
    if config:
        return config.get("configurable", {}).get(key, default)
    return default


async def llm_node(
    state: AgentState,
    config: Optional[RunnableConfig] = None,
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

    service_context = _get_service_context(config)
    if not service_context:
        logger.error(f"[{session_id}] [LLM节点] service_context 未配置")
        return {"error": "service_context 未配置", "response_text": "", "response_chunks": [], "tool_calls": None}

    llm_engine = service_context.llm_engine
    if not llm_engine:
        logger.error(f"[{session_id}] [LLM节点] LLM 引擎未初始化")
        return {"error": "LLM 引擎未初始化", "response_text": "", "response_chunks": [], "tool_calls": None}

    # 检查是否启用工具
    enable_tools = _get_config_value(config, "enable_tools", False)
    chat_model = _get_config_value(config, "chat_model", None)

    if enable_tools and chat_model:
        return await _llm_with_tools(session_id, state, service_context, chat_model, config)
    else:
        return await _llm_without_tools(session_id, state, service_context, config)


async def _llm_with_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
    chat_model: Any,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """使用工具调用模式"""
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))
    llm_engine = service_context.llm_engine

    logger.info(f"[{session_id}] [LLM节点] 使用工具调用模式")

    system_prompt = state.get("system_prompt")
    if not system_prompt and service_context.config:
        system_prompt = service_context.config.get_system_prompt()

    # 🆕 RAG: 检索记忆上下文
    memory_context = await _retrieve_memory_context(
        session_id=session_id,
        query=user_text,
        config=config,
        max_turns=5,
    )

    # 🆕 注入记忆到 system_prompt
    enriched_prompt = _enrich_system_prompt(system_prompt, memory_context)

    bound_tools = getattr(chat_model, "bound_tools", []) or getattr(chat_model, "tools", [])

    history_for_llm = [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))]

    try:
        response = await llm_engine.chat_with_tools(
            user_text,
            tools=bound_tools,
            langchain_history=history_for_llm,
            system_prompt=enriched_prompt,  # 🆕 使用增强的 prompt
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
        return await _llm_without_tools(session_id, state, service_context, config)


async def _llm_without_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """使用流式模式（无工具）"""
    user_text = state.get("user_text", "")
    llm_engine = service_context.llm_engine
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLM节点] 使用流式模式（无工具）")

    system_prompt = state.get("system_prompt", "")

    # 🆕 RAG: 检索记忆上下文
    memory_context = await _retrieve_memory_context(
        session_id=session_id,
        query=user_text,
        config=config,
        max_turns=5,
    )

    # 🆕 注入记忆到 system_prompt
    enriched_prompt = _enrich_system_prompt(system_prompt, memory_context)

    if not messages or not isinstance(messages[0], SystemMessage):
        if enriched_prompt:
            messages.insert(0, SystemMessage(content=enriched_prompt))

    user_id = state.get("user_id")
    user_name = state.get("user_name")

    if not messages or not isinstance(messages[-1], HumanMessage):
        content = f"[{user_name}]: {user_text}" if user_name else user_text
        messages.append(HumanMessage(content=content, name=user_id or "user"))

    interrupt_handler = get_interrupt_handler()
    interrupt_handler.clear_interrupt(session_id)

    chunks = []
    full_response = ""

    async for chunk in llm_engine.chat_stream(user_text, system_prompt=enriched_prompt):
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
