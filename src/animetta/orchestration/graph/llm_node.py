"""LLM inference node - supports tool calls and streaming output"""

import asyncio
import json
import time as time_module
from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from loguru import logger

from animetta.memory.v2.context import MemoryContext, normalize_actor_id
from animetta.services.bilibili.response_policy import (
    constrain_livestream_response,
    constrain_minecraft_narration_response,
    constrain_proactive_topic_response,
    is_minecraft_narration_turn,
    is_proactive_topic_turn,
)
from animetta.services.dialogue.response_processing import (
    FALLBACK_RESPONSE as FALLBACK_RESPONSE,
)
from animetta.services.dialogue.response_processing import (
    _enforce_persona_verbal_tics as _enforce_persona_verbal_tics,
)
from animetta.services.dialogue.response_processing import (
    _has_user_visible_response,
    _visible_response_or_fallback,
    process_reply,
)
from animetta.services.dialogue.response_processing import (
    _strip_emotion_tags as _strip_emotion_tags,
)
from animetta.services.dialogue.response_processing import (
    _strip_model_thinking as _strip_model_thinking,
)
from animetta.services.llm.token_counting import make_trim_token_counter

from .conversation_session import ConversationSessionState
from .interrupt_handler import get_interrupt_handler
from .memory_middleware import MemoryMiddleware
from .node_error import log_node_error
from .state import AgentState, log_timing

# Configurable timeout for LLM provider calls (default: 30 seconds)
TIMEOUT_SECONDS = 30

# Default token budget for the graph ``messages`` window (context-bloat guard).
DEFAULT_CONTEXT_TOKEN_BUDGET = 6000


def _conversation_session(config: RunnableConfig | None) -> ConversationSessionState | None:
    configurable = config.get("configurable", {}) if config else {}
    session = configurable.get("conversation_session")
    return session if isinstance(session, ConversationSessionState) else None


def _explicit_history_messages(
    current_messages: list[Any],
    state: AgentState,
    config: RunnableConfig | None,
    session_id: str,
    *,
    fixed_messages: list[Any] | None = None,
) -> list[Any]:
    """Prepend completed pairs and trim only whole oldest pairs.

    ``current_messages`` is the in-flight tool chain and is never split. The
    caller may supply system/current-user messages in ``fixed_messages`` for
    accurate budget accounting without adding them to the returned history.
    """

    session = _conversation_session(config)
    pairs = (
        [
            [HumanMessage(content=user), AIMessage(content=assistant)]
            for user, assistant in session.prompt_window
        ]
        if session is not None and not is_minecraft_narration_turn(state.get("metadata", {}))
        else []
    )
    raw_budget = state.get("max_context_tokens")
    budget = (
        int(raw_budget) if isinstance(raw_budget, (int, float)) else DEFAULT_CONTEXT_TOKEN_BUDGET
    )
    counter = make_trim_token_counter()
    fixed = fixed_messages or []
    before_pairs = len(pairs)
    if budget > 0:
        while pairs:
            combined = [message for pair in pairs for message in pair]
            if counter([*fixed, *combined, *current_messages]) <= budget:
                break
            pairs.pop(0)
    if len(pairs) != before_pairs:
        logger.info(
            "[{}] [LLMNode] Conversation budget applied: pairs {} -> {} (budget={})",
            session_id,
            before_pairs,
            len(pairs),
            budget,
        )
    return [message for pair in pairs for message in pair] + current_messages


def _provider_message(message: Any) -> dict[str, Any]:
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": str(message.content)}
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "content": str(message.content),
            "tool_call_id": message.tool_call_id,
        }
    if isinstance(message, AIMessage):
        result: dict[str, Any] = {"role": "assistant", "content": str(message.content or "")}
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": call.get("name", ""),
                        "arguments": json.dumps(call.get("args", {}), ensure_ascii=False),
                    },
                }
                for call in message.tool_calls
            ]
        return result
    raise TypeError(f"Unsupported explicit chat message: {type(message).__name__}")


def _prompt_state(state: AgentState, config: RunnableConfig | None) -> AgentState:
    session = _conversation_session(config)
    if session is None or not session.has_private_developer_context:
        return state
    return {
        **state,
        "metadata": {
            **state.get("metadata", {}),
            "has_private_developer_context": True,
        },
    }


def _has_completed_connection_call(messages: list[Any]) -> bool:
    """Return whether the latest tool result completed a connection operation."""

    if len(messages) < 2 or not isinstance(messages[-1], ToolMessage):
        return False
    tool_result = messages[-1]
    assistant = messages[-2]
    if not isinstance(assistant, AIMessage) or str(tool_result.content).startswith("Error:"):
        return False
    return any(
        call.get("id") == tool_result.tool_call_id and call.get("name") == "mc_connection"
        for call in assistant.tool_calls
    )


def _response_for_delivery(state: AgentState, text: str) -> str:
    """Apply the service-owned delivery policy selected by graph state."""
    visible = _strip_emotion_tags(text)
    metadata = state.get("metadata", {})
    if is_minecraft_narration_turn(metadata):
        max_chars = metadata.get("minecraft_narration_max_chars", 60)
        return constrain_minecraft_narration_response(
            visible,
            max_chars=int(max_chars) if isinstance(max_chars, int) else 60,
        )
    if is_proactive_topic_turn(metadata):
        max_chars = metadata.get("proactive_topic_max_chars", 36)
        recent = metadata.get("proactive_recent_outputs", [])
        return constrain_proactive_topic_response(
            visible,
            max_chars=int(max_chars) if isinstance(max_chars, int) else 36,
            recent_outputs=(recent if isinstance(recent, list) else ()),
        )
    if state.get("personality_mode") == "streaming":
        return constrain_livestream_response(visible)
    return visible


# ========================================
# RAG memory retrieval helper functions
# ========================================


def _get_memory_system(config: RunnableConfig | None) -> Any | None:
    """Get memory_system from LangGraph config"""
    if config:
        service_context = config.get("configurable", {}).get("service_context")
        if service_context and hasattr(service_context, "memory_system"):
            return service_context.memory_system
    return None


def _get_memory_middleware(config: RunnableConfig | None) -> MemoryMiddleware | None:
    """Get or create MemoryMiddleware from LangGraph config"""
    if config:
        configurable = config.get("configurable", {})
        # Explicit None means "skip middleware" (used in tests)
        if "memory_middleware" in configurable:
            return configurable["memory_middleware"]
        memory_system = _get_memory_system(config)
        if memory_system:
            middleware = MemoryMiddleware(
                memory_system=memory_system,
                observation_recorder=configurable.get("observation_recorder"),
            )
            return middleware
    return None


async def _retrieve_memory_context(
    session_id: str,
    query: str,
    config: RunnableConfig | None,
    current_emotion: Any = None,
    character_known: list[str] | None = None,
    character_unknown: list[str] | None = None,
    mbti_ei: int = 50,
    mbti_sn: int = 50,
    mbti_tf: int = 50,
    mbti_jp: int = 50,
    context: MemoryContext | None = None,
) -> tuple[str, dict]:
    """
    Retrieve memory context via LivingMemorySystem V2 recall().

    Args:
        session_id: Session ID
        query: Query text (user input)
        config: LangGraph config
        current_emotion: VADVector for mood-congruent recall
        character_known: Character's known knowledge domains (from persona config)
        character_unknown: Character's unknown knowledge domains (excluded from recall)
        mbti_ei, mbti_sn, mbti_tf, mbti_jp: MBTI dimensions for persona-biased ranking

    Returns:
        Tuple of (enriched system prompt, metadata dict)
    """
    middleware = _get_memory_middleware(config)
    if not middleware:
        logger.debug(f"[{session_id}] [LLMNode] MemoryMiddleware not available, skipping RAG")
        return "", {}

    try:
        recall = (
            middleware.recall_structured
            if isinstance(middleware, MemoryMiddleware)
            else middleware.before_llm_call
        )
        enriched, metadata = await recall(
            session_id=session_id,
            user_input=query,
            current_emotion=current_emotion,
            character_known=character_known,
            character_unknown=character_unknown,
            mbti_ei=mbti_ei,
            mbti_sn=mbti_sn,
            mbti_tf=mbti_tf,
            mbti_jp=mbti_jp,
            context=context,
        )
        if metadata:
            logger.info(f"[{session_id}] [LLMNode] Memory injected")
        return enriched, metadata or {}
    except Exception as e:
        logger.warning(f"[{session_id}] [LLMNode] MemoryMiddleware retrieval failed: {e}")
        return "", {}


def _build_memory_context(state: AgentState) -> MemoryContext:
    """Build memory identity from stable turn metadata, keeping SID trace-only."""
    metadata = state.get("metadata", {}) or {}
    persona = state.get("persona", {}) or {}
    persona_id = metadata.get("persona_id")
    if not persona_id and isinstance(persona, dict):
        persona_id = persona.get("id") or persona.get("name")
    channel = metadata.get("channel")
    return MemoryContext(
        actor_id=normalize_actor_id(
            state.get("user_id") or metadata.get("actor_id"),
            channel,
        ),
        conversation_id=metadata.get("conversation_id"),
        stream_id=metadata.get("stream_id"),
        persona_id=persona_id,
        channel=channel or "unknown",
        connection_id=state.get("session_id"),
        actor_role=metadata.get("actor_role"),
        source=metadata.get("source"),
        live_session_id=metadata.get("live_session_id"),
        message_id=state.get("message_id") or metadata.get("message_id"),
        task_id=state.get("task_id") or metadata.get("task_id"),
        turn_id=state.get("turn_id") or metadata.get("turn_id"),
        audience=metadata.get("audience"),
    )


def _get_recall_emotion(state: AgentState) -> Any | None:
    """Return audience/conversation emotion, never the model's last expression."""
    values = state.get("conversation_emotion_vad")
    if values is None:
        values = (state.get("metadata", {}) or {}).get("conversation_emotion_vad")
    if values is None:
        return None
    from animetta.memory.v2.emotion_field import VADVector

    return VADVector(*values)


def _enrich_system_prompt(
    base_prompt: str | None,
    memory_context: str,
) -> str:
    """
    Inject memory context into the system prompt.

    .. deprecated::
        Use ``orchestration.prompting.pipeline.compile()`` instead.
        Kept only for backward compatibility with existing tests and callers.
    """
    if not memory_context:
        return base_prompt or ""
    if not base_prompt:
        return memory_context

    parts = [base_prompt, memory_context]
    return "\n\n---\n\n".join(parts)


def _get_service_context(config: RunnableConfig | None) -> Any | None:
    """Get service_context from LangGraph config"""
    if config:
        return config.get("configurable", {}).get("service_context")
    return None


def _get_config_value(config: RunnableConfig | None, key: str, default: Any = None) -> Any:
    """Get config value from LangGraph config"""
    if config:
        return config.get("configurable", {}).get(key, default)
    return default


def _notify_middleware_after(
    session_id: str,
    user_input: str,
    response: str,
    config: RunnableConfig | None,
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
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """
    LLM inference node

    Input: state["user_text"], state["messages"], state["persona"]
    Output: state["messages"], state["response_text"], state["response_chunks"], state["tool_calls"]
    """
    session_id = state.get("session_id", "unknown")
    user_text = state.get("user_text", "")
    logger.info(f"[{session_id}] [LLMNode] Processing...")

    # Validate input
    if not user_text:
        logger.warning(f"[{session_id}] [LLMNode] No user text, skipping")
        return {
            "error": "No user text",
            "response_text": "",
            "response_chunks": [],
            "tool_calls": None,
        }

    service_context = _get_service_context(config)
    if not service_context:
        logger.error(f"[{session_id}] [LLMNode] service_context not configured")
        await log_node_error(session_id, "llm_node", "invalid_response", duration_ms=0)
        return {
            "error": "service_context not configured",
            "response_text": "",
            "response_chunks": [],
            "tool_calls": None,
        }

    llm_engine = service_context.llm_engine
    if not llm_engine:
        logger.error(f"[{session_id}] [LLMNode] LLM engine not initialized")
        await log_node_error(session_id, "llm_node", "invalid_response", duration_ms=0)
        return {
            "error": "LLM engine not initialized",
            "response_text": "",
            "response_chunks": [],
            "tool_calls": None,
        }

    # RAG: retrieve via LivingMemorySystem V2 recall()
    current_emotion = _get_recall_emotion(state)
    t_rag = time_module.perf_counter()
    _meta = state.get("metadata", {})
    proactive_topic = is_proactive_topic_turn(_meta)
    retrieval_result = (
        ("", {})
        if proactive_topic
        else await _retrieve_memory_context(
            session_id=session_id,
            query=user_text,
            config=config,
            current_emotion=current_emotion,
            character_known=_meta.get("character_known"),
            character_unknown=_meta.get("character_unknown"),
            mbti_ei=_meta.get("mbti_ei", 50),
            mbti_sn=_meta.get("mbti_sn", 50),
            mbti_tf=_meta.get("mbti_tf", 50),
            mbti_jp=_meta.get("mbti_jp", 50),
            context=_build_memory_context(state),
        )
    )
    memory_context, rag_metadata = (
        retrieval_result if isinstance(retrieval_result, tuple) else (retrieval_result, {})
    )
    rag_duration = (time_module.perf_counter() - t_rag) * 1000
    log_timing(state, "llm.rag_retrieval", rag_duration, f"query='{user_text[:50]}'")

    # Check if tools are enabled
    enable_tools = _get_config_value(config, "enable_tools", False) and not proactive_topic
    chat_model = _get_config_value(config, "chat_model", None)

    if enable_tools and chat_model:
        result = await _llm_with_tools(
            session_id, state, service_context, chat_model, config, memory_context
        )
    else:
        result = await _llm_without_tools(
            session_id,
            state,
            service_context,
            config,
            memory_context,
        )
    return {**result, "memory_recall": rag_metadata}


async def _llm_with_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
    chat_model: Any,
    config: RunnableConfig | None = None,
    memory_context: str = "",
) -> dict[str, Any]:
    """Use tool calling mode"""
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))
    llm_engine = service_context.llm_engine

    logger.info(f"[{session_id}] [LLMNode] Using tool calling mode")

    # Compile final system prompt via pipeline (replaces manual concatenation)
    from animetta.orchestration.prompting.pipeline import compile as compile_prompt

    compiled = await compile_prompt(
        _prompt_state(state, config), config, memory_context=memory_context
    )
    enriched_prompt = compiled.system_prompt

    if compiled.warnings:
        logger.debug(f"[{session_id}] [LLMNode] Prompt warnings: {compiled.warnings}")
    logger.info(
        f"[{session_id}] [LLMNode] Compiled prompt: {compiled.section_count} sections, "
        f"memory={compiled.memory_included}"
    )

    bound_tools = getattr(chat_model, "bound_tools", []) or getattr(chat_model, "tools", [])
    completed_tool_calls = sum(isinstance(message, ToolMessage) for message in messages)
    max_tool_calls = int(_get_config_value(config, "max_tool_calls_per_turn", 5) or 5)
    if completed_tool_calls >= max_tool_calls:
        bound_tools = []
    elif _has_completed_connection_call(messages):
        bound_tools = [
            tool for tool in bound_tools if getattr(tool, "name", None) != "mc_connection"
        ]

    current_user = HumanMessage(content=user_text)
    history_for_llm = _explicit_history_messages(
        [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))],
        state,
        config,
        session_id,
        fixed_messages=[SystemMessage(content=enriched_prompt), current_user],
    )

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

                raw_content = _visible_response_or_fallback(
                    response.get("content", "") or "Calling tools..."
                )
                visible_content = _strip_emotion_tags(raw_content)
                ai_message = AIMessage(content=visible_content, tool_calls=formatted_tool_calls)

                # after_llm_call notification (non-blocking)
                _notify_middleware_after(session_id, user_text, visible_content, config)

                response_messages: list[Any] = [ai_message]
                if not messages or not isinstance(messages[-1], ToolMessage):
                    response_messages.insert(0, HumanMessage(content=user_text))
                return {
                    "response_text": visible_content,
                    "response_chunks": [raw_content],
                    "messages": response_messages,
                    "tool_calls": formatted_tool_calls,
                }
            else:
                raw_content = response.get("content", "")
                if not _has_user_visible_response(raw_content):
                    logger.warning(
                        f"[{session_id}] [LLMNode] Tool response had no visible text; "
                        "retrying with streaming provider path"
                    )
                    return await _llm_without_tools(
                        session_id,
                        state,
                        service_context,
                        config,
                        memory_context,
                    )
                full_response = _visible_response_or_fallback(raw_content)
                logger.info(f"[{session_id}] [LLMNode] LLM response: {full_response[:100]}...")

                processed = process_reply(
                    raw_content, user_text=user_text, system_prompt=enriched_prompt
                )
                full_response = processed.text
                response_chunks = list(processed.chunks)
                affinity_update = (
                    {"affinity": processed.affinity} if processed.affinity is not None else {}
                )
                # after_llm_call notification (non-blocking)
                _notify_middleware_after(session_id, user_text, full_response, config)

                delivery_response = _response_for_delivery(state, full_response)
                if state.get("personality_mode") == "streaming":
                    response_chunks = [delivery_response]
                return {
                    "response_text": delivery_response,
                    "response_chunks": response_chunks,
                    "tool_calls": None,
                    **affinity_update,
                    "metadata": {
                        **state.get("metadata", {}),
                        **affinity_update,
                        "dialogue_status": "direct",
                    },
                }

        logger.warning(
            f"[{session_id}] [LLMNode] Tool response was not a mapping; using streaming fallback"
        )
        return await _llm_without_tools(
            session_id,
            state,
            service_context,
            config,
            memory_context,
        )

    except Exception as e:
        logger.error(f"[{session_id}] [LLMNode] Tool call failed: {e}")
        return await _llm_without_tools(session_id, state, service_context, config, memory_context)


async def _llm_without_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
    config: RunnableConfig | None = None,
    memory_context: str = "",
) -> dict[str, Any]:
    """Use streaming mode (no tools)"""
    user_text = state.get("user_text", "")
    llm_engine = service_context.llm_engine
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLMNode] Using streaming mode (no tools)")

    # Compile final system prompt via pipeline (replaces manual concatenation)
    from animetta.orchestration.prompting.pipeline import compile as compile_prompt

    compiled = await compile_prompt(
        _prompt_state(state, config), config, memory_context=memory_context
    )
    enriched_prompt = compiled.system_prompt

    user_id = state.get("user_id")
    user_name = state.get("user_name")

    if not messages or not isinstance(messages[-1], HumanMessage):
        content = f"[{user_name}]: {user_text}" if user_name else user_text
        messages.append(HumanMessage(content=content, name=user_id or "user"))
    system_messages = [SystemMessage(content=enriched_prompt)] if enriched_prompt else []
    messages = _explicit_history_messages(
        messages,
        state,
        config,
        session_id,
        fixed_messages=system_messages,
    )
    provider_messages = [_provider_message(message) for message in [*system_messages, *messages]]

    interrupt_handler = get_interrupt_handler()
    interrupt_handler.clear_interrupt(session_id)

    chunks = []
    full_response = ""
    interrupted = False

    timeout_seconds = (
        2.0
        if is_minecraft_narration_turn(state.get("metadata", {}))
        else _get_config_value(config, "llm_timeout", TIMEOUT_SECONDS)
    )

    t_llm = time_module.perf_counter()
    try:
        async with asyncio.timeout(timeout_seconds):
            async for chunk in llm_engine.chat_messages_stream(provider_messages):
                if interrupt_handler.is_interrupted(session_id):
                    logger.warning(
                        f"[{session_id}] [LLMNode] Interrupt detected, stopping generation"
                    )
                    interrupted = True
                    break
                chunks.append(chunk)
                full_response += chunk
                if len(chunks) % 10 == 0:
                    logger.debug(f"[{session_id}] [LLMNode] Received {len(chunks)} chunks...")
    except TimeoutError:
        llm_duration = (time_module.perf_counter() - t_llm) * 1000
        logger.warning(
            f"[{session_id}] [LLMNode] LLM timeout after {timeout_seconds}s, using fallback"
        )
        await log_node_error(session_id, "llm_node", "timeout", duration_ms=llm_duration)
        full_response = (
            "" if is_proactive_topic_turn(state.get("metadata", {})) else FALLBACK_RESPONSE
        )
        chunks = [full_response] if full_response else []

        # Note: no affinity marker in the FALLBACK_RESPONSE, so the value
        # carries over from the previous turn (correct behavior — we did not
        # actually talk to the 旅人, affection shouldn't shift).
        return {
            "response_text": _strip_emotion_tags(full_response),
            "response_chunks": chunks,
            "tool_calls": None,
            "metadata": {**state.get("metadata", {}), "error_type": "timeout"},
        }

    llm_duration = (time_module.perf_counter() - t_llm) * 1000

    logger.info(f"[{session_id}] [LLMNode] LLM response: {full_response[:100]}...")
    log_timing(
        state,
        "llm.api_call",
        llm_duration,
        f"chat_stream | chunks={len(chunks)} | ttfb_first_chunk=<see llm_engine.log>",
    )

    processed = process_reply(
        full_response, user_text=user_text, system_prompt=enriched_prompt, chunks=chunks
    )
    full_response = processed.text
    response_fallback = processed.fallback
    chunks = list(processed.chunks)
    affinity_update = {"affinity": processed.affinity} if processed.affinity is not None else {}

    # after_llm_call notification (non-blocking)
    if not is_proactive_topic_turn(state.get("metadata", {})):
        _notify_middleware_after(session_id, user_text, full_response, config)

    delivery_response = (
        ""
        if response_fallback and is_proactive_topic_turn(state.get("metadata", {}))
        else _response_for_delivery(state, full_response)
    )
    if state.get("personality_mode") == "streaming":
        chunks = [delivery_response]
    return {
        "response_text": delivery_response,
        "response_chunks": chunks,
        "tool_calls": None,
        **affinity_update,
        "metadata": {
            **state.get("metadata", {}),
            **affinity_update,
            "dialogue_status": "direct",
            "interrupted": interrupted,
            "response_fallback": response_fallback,
        },
    }
