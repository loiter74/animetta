"""
LLM 推理节点

负责：
1. 接收用户文本 (state["user_text"])
2. 从记忆系统检索相关上下文 (RAG)
3. 构建包含人设 + 记忆的 prompt
4. 调用 LLM 服务获取流式回复
5. 将结果写入 state
6. 支持工具调用（Tool Use）
"""

from typing import Dict, Any, List, Optional, Any
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from ..state import AgentState
from ..config_store import get_service_context, get_config_value


async def llm_node(
    state: AgentState,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    LLM 推理节点（支持工具调用）

    输入: state["user_text"], state["messages"], state["persona"]
    输出: state["messages"] (追加 AI 回复), state["response_text"],
          state["response_chunks"] (流式块), state["tool_calls"] (如果有)

    Args:
        state: 当前状态
        config: LangGraph 传入的运行时配置（自动注入）

    Returns:
        状态更新字典
    """
    session_id = state.get("session_id", "unknown")
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLM节点] 开始处理...")

    # ========================================
    # 验证输入
    # ========================================
    if not user_text:
        logger.warning(f"[{session_id}] [LLM节点] 无用户文本，跳过")
        return {
            "error": "无用户文本",
            "response_text": "",
            "response_chunks": [],
            "tool_calls": None,
        }

    # 从 ConfigStore 获取 service_context
    service_context = get_service_context(session_id)

    if not service_context:
        logger.error(f"[{session_id}] [LLM节点] service_context 未配置")
        return {
            "error": "service_context 未配置",
            "response_text": "",
            "response_chunks": [],
            "tool_calls": None,
        }

    llm_engine = service_context.llm_engine

    if not llm_engine:
        logger.error(f"[{session_id}] [LLM节点] LLM 引擎未初始化")
        return {
            "error": "LLM 引擎未初始化",
            "response_text": "",
            "response_chunks": [],
            "tool_calls": None,
        }

    # ========================================
    # 检查是否启用工具
    # ========================================
    enable_tools = get_config_value(session_id, "enable_tools", False)
    chat_model = get_config_value(session_id, "chat_model", None)

    logger.info(f"[{session_id}] [LLM节点] enable_tools={enable_tools}, 类型={type(enable_tools)}")
    logger.info(f"[{session_id}] [LLM节点] chat_model={'存在' if chat_model else '不存在'}")

    if enable_tools and chat_model:
        # 使用支持工具调用的底层服务
        return await _llm_with_tools(session_id, state, service_context, chat_model)
    else:
        # 使用原有的流式接口（不支持工具）
        return await _llm_without_tools(session_id, state, service_context)


async def _llm_with_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
    chat_model: Any,
) -> Dict[str, Any]:
    """
    使用底层 LLM 服务的工具调用功能

    Args:
        session_id: 会话 ID
        state: 当前状态
        service_context: 服务上下文
        chat_model: LangChain ChatModel（用于获取 bound_tools）

    Returns:
        状态更新字典
    """
    user_text = state.get("user_text", "")
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLM节点] 使用工具调用模式")

    llm_engine = service_context.llm_engine

    # 获取系统提示词
    system_prompt = state.get("system_prompt")
    if not system_prompt and service_context.config:
        system_prompt = service_context.config.get_system_prompt()

    # 获取绑定的工具
    bound_tools = getattr(chat_model, "bound_tools", [])
    if not bound_tools:
        bound_tools = getattr(chat_model, "tools", [])

    # 构建历史消息列表（排除系统消息，会单独传递）
    history_for_llm = []
    for msg in messages:
        if isinstance(msg, (HumanMessage, AIMessage, ToolMessage)):
            history_for_llm.append(msg)
        elif isinstance(msg, SystemMessage):
            # 系统消息不包含在历史中，会通过 system_prompt 参数传递
            pass

    logger.debug(f"[{session_id}] [LLM节点] 历史消息数: {len(history_for_llm)}")

    # 调用底层 LLM 服务
    try:
        response = await llm_engine.chat_with_tools(
            user_text,
            tools=bound_tools,
            langchain_history=history_for_llm,
            system_prompt=system_prompt,
        )

        # 解析响应
        if isinstance(response, dict):
            if response.get("tool_calls"):
                # 工具调用
                tool_calls = response["tool_calls"]
                formatted_tool_calls = [
                    {
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {}),
                    }
                    for tc in tool_calls
                ]

                ai_message = AIMessage(
                    content=response.get("content", "") or "正在调用工具...",
                    tool_calls=tool_calls,
                )

                return {
                    "response_text": response.get("content", "") or "正在调用工具...",
                    "response_chunks": [response.get("content", "") or ""],
                    "messages": [ai_message],
                    "tool_calls": formatted_tool_calls,
                }
            else:
                # 正常回复
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
        # 降级到无工具模式
        return await _llm_without_tools(session_id, state, service_context)


async def _llm_without_tools(
    session_id: str,
    state: AgentState,
    service_context: Any,
) -> Dict[str, Any]:
    """
    使用原有的流式接口（不支持工具）

    Args:
        session_id: 会话 ID
        state: 当前状态
        service_context: 服务上下文

    Returns:
        状态更新字典
    """
    user_text = state.get("user_text", "")
    llm_engine = service_context.llm_engine
    messages = list(state.get("messages", []))

    logger.info(f"[{session_id}] [LLM节点] 使用流式模式（无工具）")

    # ========================================
    # 获取系统提示词（如果已有）
    # ========================================
    system_prompt = state.get("system_prompt", "")

    # 如果 messages 为空或第一条不是系统消息，添加系统提示词
    if not messages or not isinstance(messages[0], SystemMessage):
        if system_prompt:
            messages.insert(0, SystemMessage(content=system_prompt))
            logger.debug(f"[{session_id}] [LLM节点] 已添加系统提示词")

    # 确保用户消息在最后
    user_id = state.get("user_id")
    user_name = state.get("user_name")

    # 如果最后一条消息不是用户消息，添加用户消息
    if not messages or not isinstance(messages[-1], HumanMessage):
        content = user_text
        if user_name:
            content = f"[{user_name}]: {user_text}"

        messages.append(HumanMessage(
            content=content,
            name=user_id or "user",
        ))

    # ========================================
    # 调用 LLM 流式接口
    # ========================================
    logger.debug(f"[{session_id}] [LLM节点] 调用 LLM 流式接口...")

    chunks = []
    full_response = ""

    # 调用现有 LLM 服务的 chat_stream 方法
    async for chunk in llm_engine.chat_stream(user_text, system_prompt=system_prompt):
        chunks.append(chunk)
        full_response += chunk

        # 日志：每 50 个字符记录一次
        if len(chunks) % 10 == 0:
            logger.debug(f"[{session_id}] [LLM节点] 已接收 {len(chunks)} 个块...")

    logger.info(f"[{session_id}] [LLM节点] LLM 回复: {full_response[:100]}...")

    # ========================================
    # 构建 AI 消息
    # ========================================
    ai_message = AIMessage(content=full_response)

    # ========================================
    # 返回状态更新
    # ========================================
    return {
        "response_text": full_response,
        "response_chunks": chunks,
        "messages": [ai_message],
        "tool_calls": None,
        "metadata": {
            **state.get("metadata", {}),
        },
    }
