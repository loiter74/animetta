"""LangGraph state definition"""

from typing import TypedDict, Annotated, Sequence, Optional, Any, Dict, List, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph Agent state"""

    # Input
    input_type: str
    raw_audio: Optional[bytes]
    user_text: str

    # LLM conversation
    messages: Annotated[Sequence[BaseMessage], add_messages]
    system_prompt: Optional[str]

    # Tool calling
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_results: Optional[List[Dict[str, Any]]]

    # Output
    response_text: str
    response_chunks: List[str]
    tts_audio: Optional[Union[bytes, str]]
    emotion: Optional[str]
    emotion_vad: Optional[tuple[float, float, float]]  # VAD vector from emotion_node

    # Control
    control_signal: Optional[str]

    # Metadata
    session_id: str
    persona: Optional[Dict[str, Any]]
    channel_id: Optional[str]
    user_id: Optional[str]
    user_name: Optional[str]
    metadata: Dict[str, Any]

    # Error handling
    error: Optional[str]
    should_retry: bool
    retry_count: int

    # Performance timing (collected at runtime for analysis)
    _timings: List[Dict[str, Any]]

    # Personality
    personality_mode: str              # 'default' | 'streaming' | 'mood_xxx'
    personality_mood: Optional[str]    # current mood override


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
    """Create initial state"""
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
        "emotion_vad": None,
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
        "_timings": [],
        "personality_mode": "default",
        "personality_mood": None,
    }


def create_user_message(text: str, user_id: Optional[str] = None, user_name: Optional[str] = None) -> HumanMessage:
    """Create user message"""
    content = f"[{user_name}]: {text}" if user_name else text
    return HumanMessage(content=content, name=user_id or "user")


def create_ai_message(text: str) -> AIMessage:
    """Create AI message"""
    return AIMessage(content=text)


def create_system_message(text: str) -> SystemMessage:
    """Create system message"""
    return SystemMessage(content=text)


# ---------------------------------------------------------------------------
# Timing helper – appends timing entries to AgentState._timings
# ---------------------------------------------------------------------------

def log_timing(state: AgentState, step: str, duration_ms: float, detail: str = "") -> None:
    """Append a timing entry to the state for performance analysis."""
    timings = state.get("_timings", [])
    timings.append({
        "step": step,
        "duration_ms": round(duration_ms, 2),
        "detail": detail,
    })
    state["_timings"] = timings
