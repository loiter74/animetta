"""Emotion analysis node"""

from typing import Dict, Any, Optional
from loguru import logger
from langgraph.types import RunnableConfig

from .state import AgentState


def _get_from_config(config: Optional[RunnableConfig], key: str) -> Optional[Any]:
    """Get value from LangGraph config"""
    if config:
        return config.get("configurable", {}).get(key)
    return None


async def emotion_node(
    state: AgentState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    Emotion analysis node

    Input: state["response_text"]
    Output: state["emotion"]
    """
    session_id = state.get("session_id", "unknown")
    response_text = state.get("response_text", "")

    logger.info(f"[{session_id}] [EmotionNode] Starting analysis...")

    if not response_text:
        logger.warning(f"[{session_id}] [EmotionNode] No response text, using default emotion")
        return {"emotion": "neutral"}

    # Get emotion_analyzer from config
    emotion_analyzer = _get_from_config(config, "emotion_analyzer")

    if not emotion_analyzer:
        # Try to get from service_context
        service_context = _get_from_config(config, "service_context")
        if service_context and hasattr(service_context, "emotion_analyzer"):
            emotion_analyzer = service_context.emotion_analyzer

    if not emotion_analyzer:
        logger.debug(f"[{session_id}] [EmotionNode] No emotion analyzer, using default emotion")
        return {"emotion": "neutral"}

    try:
        logger.debug(f"[{session_id}] [EmotionNode] Calling emotion analyzer...")

        result = emotion_analyzer.extract(response_text)
        primary_emotion = result.primary
        confidence = result.confidence

        logger.info(f"[{session_id}] [EmotionNode] Analysis result: {primary_emotion} (confidence: {confidence:.2f})")

        return {"emotion": primary_emotion}

    except Exception as e:
        logger.error(f"[{session_id}] [EmotionNode] Analysis failed: {e}")
        return {"emotion": "neutral"}
