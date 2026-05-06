"""TTS node - text to speech"""

import time as time_module
from typing import Dict, Any, Optional
from loguru import logger
from langgraph.types import RunnableConfig

from .state import AgentState, log_timing


def _get_service_context(config: Optional[RunnableConfig]) -> Optional[Any]:
    """Get service_context from LangGraph config"""
    if config:
        return config.get("configurable", {}).get("service_context")
    return None


async def tts_node(
    state: AgentState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    TTS speech synthesis node

    Input: state["response_text"]
    Output: state["tts_audio"] (bytes or str)
    """
    session_id = state.get("session_id", "unknown")
    response_text = state.get("response_text", "")

    logger.info(f"[{session_id}] [TTSNode] Starting processing...")

    if not response_text:
        logger.warning(f"[{session_id}] [TTSNode] No response text, skipping")
        return {"tts_audio": None}

    service_context = _get_service_context(config)
    if not service_context:
        logger.error(f"[{session_id}] [TTSNode] service_context not configured")
        return {"error": "service_context not configured", "tts_audio": None}

    tts_engine = service_context.tts_engine
    if not tts_engine:
        logger.warning(f"[{session_id}] [TTSNode] TTS engine not initialized, skipping")
        return {"tts_audio": None}

    logger.debug(f"[{session_id}] [TTSNode] Text length: {len(response_text)} characters")

    audio = await tts_engine.synthesize(response_text)

    if isinstance(audio, bytes):
        logger.info(f"[{session_id}] [TTSNode] Audio data: {len(audio)} bytes")
    elif isinstance(audio, str):
        logger.info(f"[{session_id}] [TTSNode] Audio file: {audio}")

    return {"tts_audio": audio}
