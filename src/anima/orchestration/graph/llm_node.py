"""LLM inference node - supports tool calls and streaming output"""

from typing import Dict, Any, List, Optional
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.types import RunnableConfig

from .state import AgentState
from .interrupt_handler import get_interrupt_handler


# ========================================
# RAG memory retrieval helper functions
# ========================================

def _get_memory_system(config: Optional[RunnableConfig]) -> Optional[Any]:
    """Get memory_system from LangGraph config"""
    if config:
        service_context = config.get("configurable", {}).get("service_context")
        if service_context and hasattr(service_context, "memory_system"):
            return service_context.memory_system
    return None


def _format_memory_context(memory_turns: List[Any], max_items: int = 5) -> str:
    """
    Format memory context as text

    Args:
        memory_turns: List of MemoryTurn objects
        max_items: Maximum number of items to display

    Returns:
        Formatted memory text
    """
    if not memory_turns:
        return ""

    # Only take the first max_items entries
    selected = memory_turns[:max_items]

    lines = ["## Related Memories"]
    for i, turn in enumerate(selected, 1):
        # Prefer oral version if available
        if hasattr(turn, "metadata"):
            oral = turn.metadata.get("oral_version")
        else:
            oral = None

        user_text = turn.user_input if hasattr(turn, "user_input") else ""
        agent_text = turn.agent_response if hasattr(turn, "agent_response") else ""

        if oral:
            lines.append(f"{i}. {oral}")
        else:
            # Compatible with old data: use original text when no oral version
            if user_text and agent_text:
                lines.append(f"{i}. You said: {user_text}")
                lines.append(f"   I replied: {agent_text}")
            elif user_text:
                lines.append(f"{i}. You said: {user_text}")

    return "\n".join(lines) if len(lines) > 1 else ""


async def _retrieve_memory_context(
    session_id: str,
    query: str,
    config: Optional[RunnableConfig],
    max_turns: int = 5,
) -> str:
    """
    Retrieve memory context

    Args:
        session_id: Session ID
        query: Query text (user input)
        config: LangGraph config
        max_turns: Maximum number of turns to retrieve

    Returns:
        Formatted memory text
    """
    memory_system = _get_memory_system(config)
    if not memory_system:
        logger.debug(f"[{session_id}] [LLMNode] MemorySystem not configured, skipping RAG")
        return ""

    try:
        memory_turns = await memory_system.retrieve_context(
            query=query,
            session_id=session_id,
            max_turns=max_turns,
        )

        if memory_turns:
            context = _format_memory_context(memory_turns, max_items=max_turns)
            logger.info(f"[{session_id}] [LLMNode] RAG retrieved {len(memory_turns)} memory entries")
            logger.debug(f"[{session_id}] [LLMNode] Memory context: {context[:200]}...")
            return context
        else:
            logger.debug(f"[{session_id}] [LLMNode] RAG found no related memories")
            return ""

    except Exception as e:
        logger.warning(f"[{session_id}] [LLMNode] RAG retrieval failed: {e}")
        return ""


def _enrich_system_prompt(
    base_prompt: Optional[str],
    memory_context: str,
) -> str:
    """
    Inject memory context into the system prompt

    Args:
        base_prompt: Base system prompt
        memory_context: Memory context text

    Returns:
        Enriched system prompt
    """
    if not memory_context:
        return base_prompt or ""

    parts = []
    if base_prompt:
        parts.append(base_prompt)

    # Add memory context
    parts.append(memory_context)

    # Add instruction
    parts.append("\nPlease refer to the above memories and answer the user's question naturally. If no relevant information is in the memories, respond normally.")

    return "\n\n---\n\n".join(parts)


def _get_service_context(config: Optional[RunnableConfig]) -> Optional[Any]:
    """Get service_context from LangGraph config"""
    if config:
        return config.get("configurable", {}).get("service_context")
    return None


def _get_config_value(config: Optional[RunnableConfig], key: str, default: Any = None) -> Any:
    """Get config value from LangGraph config"""
    if config:
        return config.get("configurable", {}).get(key, default)
    return default


async def llm_node(
    state: AgentState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    LLM inference node

    Input: state["user_text"], state["messages"], state["persona"]
    Output: state["messages"], state["response_text"], state["response_chunks"], state["tool_calls"]
    """
    session_id = state.get("session_id", "unknown")
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLMNode] Processing...")

    # Validate input
    if not user_text:
        logger.warning(f"[{session_id}] [LLMNode] No user text, skipping")
        return {"error": "No user text", "response_text": "", "response_chunks": [], "tool_calls": None}

    service_context = _get_service_context(config)
    if not service_context:
        logger.error(f"[{session_id}] [LLMNode] service_context not configured")
        return {"error": "service_context not configured", "response_text": "", "response_chunks": [], "tool_calls": None}

    llm_engine = service_context.llm_engine
    if not llm_engine:
        logger.error(f"[{session_id}] [LLMNode] LLM engine not initialized")
        return {"error": "LLM engine not initialized", "response_text": "", "response_chunks": [], "tool_calls": None}

    # Check if tools are enabled
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
    """Use tool calling mode"""
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))
    llm_engine = service_context.llm_engine

    logger.info(f"[{session_id}] [LLMNode] Using tool calling mode")

    system_prompt = state.get("system_prompt")
    if not system_prompt and service_context.config:
        system_prompt = service_context.config.get_system_prompt()

    # RAG: retrieve memory context
    memory_context = await _retrieve_memory_context(
        session_id=session_id,
        query=user_text,
        config=config,
        max_turns=5,
    )

    # Inject memory into system_prompt
    enriched_prompt = _enrich_system_prompt(system_prompt, memory_context)

    bound_tools = getattr(chat_model, "bound_tools", []) or getattr(chat_model, "tools", [])

    history_for_llm = [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))]

    try:
        response = await llm_engine.chat_with_tools(
            user_text,
            tools=bound_tools,
            langchain_history=history_for_llm,
            system_prompt=enriched_prompt,  # Use enriched prompt
        )

        if isinstance(response, dict):
            if response.get("tool_calls"):
                tool_calls = response["tool_calls"]
                formatted_tool_calls = [
                    {"id": tc.get("id", ""), "name": tc.get("name", ""), "args": tc.get("args", {})}
                    for tc in tool_calls
                ]

                ai_message = AIMessage(content=response.get("content", "") or "Calling tools...", tool_calls=tool_calls)

                return {
                    "response_text": response.get("content", "") or "Calling tools...",
                    "response_chunks": [response.get("content", "") or ""],
                    "messages": [ai_message],
                    "tool_calls": formatted_tool_calls,
                }
            else:
                full_response = response.get("content", "")
                logger.info(f"[{session_id}] [LLMNode] LLM response: {full_response[:100]}...")
                ai_message = AIMessage(content=full_response)

                return {
                    "response_text": full_response,
                    "response_chunks": [full_response],
                    "messages": [ai_message],
                    "tool_calls": None,
                }

    except Exception as e:
        logger.error(f"[{session_id}] [LLMNode] Tool call failed: {e}")
        return await _llm_without_tools(session_id, state, service_context, config)


async def _llm_without_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """Use streaming mode (no tools)"""
    user_text = state.get("user_text", "")
    llm_engine = service_context.llm_engine
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLMNode] Using streaming mode (no tools)")

    system_prompt = state.get("system_prompt", "")

    # RAG: retrieve memory context
    memory_context = await _retrieve_memory_context(
        session_id=session_id,
        query=user_text,
        config=config,
        max_turns=5,
    )

    # Inject memory into system_prompt
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
            logger.warning(f"[{session_id}] [LLMNode] Interrupt detected, stopping generation")
            break
        chunks.append(chunk)
        full_response += chunk
        if len(chunks) % 10 == 0:
            logger.debug(f"[{session_id}] [LLMNode] Received {len(chunks)} chunks...")

    logger.info(f"[{session_id}] [LLMNode] LLM response: {full_response[:100]}...")

    ai_message = AIMessage(content=full_response)

    return {
        "response_text": full_response,
        "response_chunks": chunks,
        "messages": [ai_message],
        "tool_calls": None,
        "metadata": {**state.get("metadata", {})},
    }
