"""LLM inference node - supports tool calls and streaming output"""

from typing import Dict, Any, List, Optional
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.types import RunnableConfig

import time as time_module

from .state import AgentState, log_timing
from .interrupt_handler import get_interrupt_handler
from .memory_middleware import MemoryMiddleware


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


def _get_memory_middleware(config: Optional[RunnableConfig]) -> Optional[MemoryMiddleware]:
    """Get or create MemoryMiddleware from LangGraph config"""
    if config:
        existing = config.get("configurable", {}).get("memory_middleware")
        if existing:
            return existing
        memory_system = _get_memory_system(config)
        if memory_system:
            middleware = MemoryMiddleware(memory_system=memory_system)
            return middleware
    return None


async def _retrieve_memory_context(
    session_id: str,
    query: str,
    config: Optional[RunnableConfig],
    max_turns: int = 5,
) -> str:
    """
    Retrieve memory context via MemoryMiddleware

    Args:
        session_id: Session ID
        query: Query text (user input)
        config: LangGraph config
        max_turns: Maximum number of turns to retrieve

    Returns:
        Enriched system prompt with memory and profile
    """
    middleware = _get_memory_middleware(config)
    if not middleware:
        logger.debug(f"[{session_id}] [LLMNode] MemoryMiddleware not available, skipping RAG")
        return ""

    try:
        enriched, metadata = await middleware.before_llm_call(
            session_id=session_id,
            user_input=query,
        )
        if metadata and metadata.get("memory_count", 0) > 0:
            logger.info(f"[{session_id}] [LLMNode] Middleware injected {metadata['memory_count']} memories")
        return enriched
    except Exception as e:
        logger.warning(f"[{session_id}] [LLMNode] MemoryMiddleware retrieval failed: {e}")
        return ""


def _enrich_system_prompt(
    base_prompt: Optional[str],
    memory_context: str,
) -> str:
    """
    Inject memory context into the system prompt

    Note: When MemoryMiddleware is active, memory_context is already
    a fully-enriched prompt. This function is kept for backward compatibility.

    Args:
        base_prompt: Base system prompt
        memory_context: Memory context / enriched prompt text

    Returns:
        Enriched system prompt
    """
    if not memory_context:
        return base_prompt or ""
    if not base_prompt:
        return memory_context

    parts = [base_prompt, memory_context]
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


def _notify_middleware_after(
    session_id: str,
    user_input: str,
    response: str,
    config: Optional[RunnableConfig],
) -> None:
    """Non-blocking notification to middleware that LLM call is complete."""
    try:
        import asyncio
        middleware = _get_memory_middleware(config)
        if middleware:
            asyncio.ensure_future(
                middleware.after_llm_call(
                    session_id=session_id,
                    user_input=user_input,
                    agent_response=response,
                )
            )
    except Exception as e:
        logger.debug(f"[{session_id}] [LLMNode] middleware after_llm_call notification failed: {e}")


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

    t0 = time_module.perf_counter()

    system_prompt = state.get("system_prompt")
    if not system_prompt and service_context.config:
        system_prompt = service_context.config.get_system_prompt()

    # RAG + Profile: retrieve via MemoryMiddleware
    t_rag = time_module.perf_counter()
    memory_context = await _retrieve_memory_context(
        session_id=session_id,
        query=user_text,
        config=config,
        max_turns=5,
    )
    rag_duration = (time_module.perf_counter() - t_rag) * 1000
    log_timing(state, "llm.rag_retrieval", rag_duration, f"query='{user_text[:50]}'")

    # Inject memory into system_prompt
    enriched_prompt = _enrich_system_prompt(system_prompt, memory_context)

    bound_tools = getattr(chat_model, "bound_tools", []) or getattr(chat_model, "tools", [])

    history_for_llm = [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))]

    try:
        t_llm = time_module.perf_counter()
        response = await llm_engine.chat_with_tools(
            user_text,
            tools=bound_tools,
            langchain_history=history_for_llm,
            system_prompt=enriched_prompt,  # Use enriched prompt
        )
        llm_duration = (time_module.perf_counter() - t_llm) * 1000
        log_timing(state, "llm.api_call", llm_duration, "chat_with_tools")

        if isinstance(response, dict):
            if response.get("tool_calls"):
                tool_calls = response["tool_calls"]
                formatted_tool_calls = [
                    {"id": tc.get("id", ""), "name": tc.get("name", ""), "args": tc.get("args", {})}
                    for tc in tool_calls
                ]

                ai_message = AIMessage(content=response.get("content", "") or "Calling tools...", tool_calls=tool_calls)

                # after_llm_call notification (non-blocking)
                _notify_middleware_after(session_id, user_text, response.get("content", ""), config)

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

                # after_llm_call notification (non-blocking)
                _notify_middleware_after(session_id, user_text, full_response, config)

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

    t0 = time_module.perf_counter()

    system_prompt = state.get("system_prompt", "")

    # RAG: retrieve memory context
    t_rag = time_module.perf_counter()
    memory_context = await _retrieve_memory_context(
        session_id=session_id,
        query=user_text,
        config=config,
        max_turns=5,
    )
    rag_duration = (time_module.perf_counter() - t_rag) * 1000
    log_timing(state, "llm.rag_retrieval", rag_duration, f"query='{user_text[:50]}'")

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

    t_llm = time_module.perf_counter()
    async for chunk in llm_engine.chat_stream(user_text, system_prompt=enriched_prompt):
        if interrupt_handler.is_interrupted(session_id):
            logger.warning(f"[{session_id}] [LLMNode] Interrupt detected, stopping generation")
            break
        chunks.append(chunk)
        full_response += chunk
        if len(chunks) % 10 == 0:
            logger.debug(f"[{session_id}] [LLMNode] Received {len(chunks)} chunks...")
    llm_duration = (time_module.perf_counter() - t_llm) * 1000

    logger.info(f"[{session_id}] [LLMNode] LLM response: {full_response[:100]}...")
    log_timing(state, "llm.api_call", llm_duration,
               f"chat_stream | chunks={len(chunks)} | ttfb_first_chunk=<see llm_engine.log>")

    ai_message = AIMessage(content=full_response)

    # after_llm_call notification (non-blocking)
    _notify_middleware_after(session_id, user_text, full_response, config)

    return {
        "response_text": full_response,
        "response_chunks": chunks,
        "messages": [ai_message],
        "tool_calls": None,
        "metadata": {**state.get("metadata", {})},
    }
