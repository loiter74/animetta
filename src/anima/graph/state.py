"""
LangGraph 状态定义

定义 AgentState，包含整个对话流程中需要传递的所有数据。
使用 LangGraph 的 Annotated 类型和 reducer 函数处理消息列表的追加。
"""

from typing import TypedDict, Annotated, Sequence, Optional, Any, Dict, List
from typing import Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages


def _default_messages_reducer(
    current: List[BaseMessage],
    new: List[BaseMessage]
) -> List[BaseMessage]:
    """
    自定义消息列表 reducer

    用于处理消息历史，确保新消息正确追加。

    Args:
        current: 当前消息列表
        new: 新增消息

    Returns:
        合并后的消息列表
    """
    return add_messages(current, new)


class AgentState(TypedDict):
    """
    LangGraph Agent 状态

    包含整个对话流程中需要传递的所有数据。
    每个节点读取/修改状态中的特定字段。
    """

    # ========================================
    # 输入相关字段
    # ========================================
    input_type: str
    """输入类型: 'text' 或 'audio'"""

    raw_audio: Optional[bytes]
    """原始音频数据（当 input_type='audio' 时）"""

    user_text: str
    """用户文本（直接输入或 ASR 识别结果）"""

    # ========================================
    # LLM 对话相关字段
    # ========================================
    messages: Annotated[Sequence[BaseMessage], add_messages]
    """
    完整对话消息历史

    使用 add_messages reducer，确保新消息追加而非覆盖。
    包含 SystemMessage, HumanMessage, AIMessage 等。
    """

    system_prompt: Optional[str]
    """系统提示词（包含人设）"""

    # ========================================
    # 工具调用相关字段
    # ========================================
    tool_calls: Optional[List[Dict[str, Any]]]
    """
    LLM 请求的工具调用列表

    格式: [{"id": str, "name": str, "args": dict}, ...]
    """

    tool_results: Optional[List[Dict[str, Any]]]
    """
    工具执行结果列表

    格式: [{"tool_call_id": str, "result": Any}, ...]
    """

    # ========================================
    # 输出相关字段
    # ========================================
    response_text: str
    """LLM 最终回复文本（完整拼接）"""

    response_chunks: List[str]
    """流式输出的文本块列表"""

    tts_audio: Optional[Union[bytes, str]]
    """
    TTS 合成的音频数据

    可能是:
    - bytes: 音频字节数据
    - str: 音频文件路径
    """

    emotion: Optional[str]
    """
    情感标签（用于 Live2D 表情）

    可选值: "happy", "sad", "angry", "surprised", "thinking", "neutral"
    """

    # ========================================
    # 控制相关字段
    # ========================================
    control_signal: Optional[str]
    """
    控制信号

    用于控制对话流程，如开始/结束会话、打断等
    """

    # ========================================
    # 元数据字段
    # ========================================
    session_id: str
    """会话 ID（关联到 ServiceContext）"""

    persona: Optional[Dict[str, Any]]
    """
    角色人设配置

    包含 name, identity, personality, behavior 等
    """

    channel_id: Optional[str]
    """通道 ID（用于回复）"""

    user_id: Optional[str]
    """用户 ID（多用户场景）"""

    user_name: Optional[str]
    """用户显示名称"""

    metadata: Dict[str, Any]
    """
    额外元数据

    用于传递节点间需要的临时数据
    """

    # ========================================
    # 错误处理字段
    # ========================================
    error: Optional[str]
    """错误信息（如果有）"""

    should_retry: bool
    """是否应该重试（工具调用失败时）"""

    retry_count: int
    """重试次数"""

    # ========================================
    # 内部配置字段（用于传递服务上下文）
    # ========================================
    _config: Optional[Dict[str, Any]]
    """
    内部配置（由 Orchestrator 注入）

    包含 service_context, socketio, emotion_analyzer 等。
    这个字段不在 API 中暴露，仅用于内部节点访问配置。
    """


def create_initial_state(
    session_id: str,
    input_type: str = "text",
    user_text: str = "",
    raw_audio: Optional[bytes] = None,
    persona: Optional[Dict[str, Any]] = None,
    system_prompt: Optional[str] = None,
    channel_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
) -> AgentState:
    """
    创建初始状态

    Args:
        session_id: 会话 ID
        input_type: 输入类型
        user_text: 用户文本
        raw_audio: 原始音频（可选）
        persona: 人设配置（可选）
        system_prompt: 系统提示词（可选）
        channel_id: 通道 ID（可选）
        user_id: 用户 ID（可选）
        user_name: 用户名称（可选）

    Returns:
        AgentState: 初始状态字典
    """
    return {
        "input_type": input_type,
        "raw_audio": raw_audio,
        "user_text": user_text,
        "messages": [],
        "system_prompt": system_prompt,
        "tool_calls": None,
        "tool_results": None,
        "response_text": "",
        "response_chunks": [],
        "tts_audio": None,
        "emotion": None,
        "control_signal": None,
        "session_id": session_id,
        "persona": persona or {},
        "channel_id": channel_id,
        "user_id": user_id,
        "user_name": user_name,
        "metadata": {},
        "error": None,
        "should_retry": False,
        "retry_count": 0,
    }


def create_user_message(text: str, user_id: Optional[str] = None, user_name: Optional[str] = None) -> HumanMessage:
    """
    创建用户消息

    Args:
        text: 消息文本
        user_id: 用户 ID（可选）
        user_name: 用户名称（可选）

    Returns:
        HumanMessage: 用户消息对象
    """
    content = text
    if user_name:
        content = f"[{user_name}]: {text}"

    return HumanMessage(
        content=content,
        name=user_id or "user",
    )


def create_ai_message(text: str) -> AIMessage:
    """
    创建 AI 消息

    Args:
        text: 消息文本

    Returns:
        AIMessage: AI 消息对象
    """
    return AIMessage(content=text)


def create_system_message(text: str) -> SystemMessage:
    """
    创建系统消息

    Args:
        text: 系统提示词

    Returns:
        SystemMessage: 系统消息对象
    """
    return SystemMessage(content=text)
