"""ASR 节点 - 音频转文本"""

from typing import Dict, Any, Optional
from loguru import logger
from langchain_core.messages import HumanMessage

from .state import AgentState


def _get_service_context(config: Optional[Dict[str, Any]]) -> Optional[Any]:
    """从 LangGraph config 获取 service_context"""
    if config:
        return config["configurable"] if config else {}.get("service_context")
    return None


async def asr_node(
    state: AgentState,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    ASR 语音识别节点

    输入: state["raw_audio"] (bytes)
    输出: state["user_text"] (str), state["messages"]
    """
    session_id = state.get("session_id", "unknown")
    raw_audio = state.get("raw_audio")

    logger.info(f"[{session_id}] [ASR节点] 开始处理音频...")

    if not raw_audio:
        logger.warning(f"[{session_id}] [ASR节点] 无音频数据，跳过")
        return {"error": "无音频数据", "user_text": ""}

    service_context = _get_service_context(config)
    if not service_context:
        logger.error(f"[{session_id}] [ASR节点] service_context 未配置")
        return {"error": "service_context 未配置", "user_text": ""}

    asr_engine = service_context.asr_engine
    if not asr_engine:
        logger.error(f"[{session_id}] [ASR节点] ASR 引擎未初始化")
        return {"error": "ASR 引擎未初始化", "user_text": ""}

    text = await asr_engine.transcribe(raw_audio)
    logger.info(f"[{session_id}] [ASR节点] 识别结果: {text[:50]}...")

    user_id = state.get("user_id")
    user_name = state.get("user_name")

    content = f"[{user_name}]: {text}" if user_name else text
    message = HumanMessage(content=content, name=user_id or "user")

    return {"user_text": text, "messages": [message]}
