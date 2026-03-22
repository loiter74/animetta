"""LangGraph 状态定义"""

from typing import TypedDict, Annotated, Sequence, Optional, Any, Dict, List, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph Agent 状态"""

    # 输入
    input_type: str
    raw_audio: Optional[bytes]
    user_text: str

    # LLM 对话
    messages: Annotated[Sequence[BaseMessage], add_messages]
    system_prompt: Optional[str]

    # 工具调用
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_results: Optional[List[Dict[str, Any]]]

    # 输出
    response_text: str
    response_chunks: List[str]
    tts_audio: Optional[Union[bytes, str]]
    emotion: Optional[str]

    # 控制
    control_signal: Optional[str]

    # 元数据
    session_id: str
    persona: Optional[Dict[str, Any]]
    channel_id: Optional[str]
    user_id: Optional[str]
    user_name: Optional[str]
    metadata: Dict[str, Any]

    # 错误处理
    error: Optional[str]
    should_retry: bool
    retry_count: int

    # 内部配置
    _config: Optional[Dict[str, Any]]


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
    """创建初始状态"""
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
    """创建用户消息"""
    content = f"[{user_name}]: {text}" if user_name else text
    return HumanMessage(content=content, name=user_id or "user")


def create_ai_message(text: str) -> AIMessage:
    """创建 AI 消息"""
    return AIMessage(content=text)


def create_system_message(text: str) -> SystemMessage:
    """创建系统消息"""
    return SystemMessage(content=text)
