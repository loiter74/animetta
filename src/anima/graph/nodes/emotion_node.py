"""情感分析节点"""

from typing import Dict, Any, Optional
from loguru import logger

from ..state import AgentState


async def emotion_node(
    state: AgentState,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    情感分析节点

    输入: state["response_text"]
    输出: state["emotion"]
    """
    session_id = state.get("session_id", "unknown")
    response_text = state.get("response_text", "")

    logger.info(f"[{session_id}] [情感节点] 开始分析...")

    if not response_text:
        logger.warning(f"[{session_id}] [情感节点] 无回复文本，使用默认情感")
        return {"emotion": "neutral"}

    if config is None:
        config = state.get("_config", {})

    try:
        emotion_analyzer = (config if config else {}).get("configurable", {}).get("emotion_analyzer")

        if not emotion_analyzer:
            logger.debug(f"[{session_id}] [情感节点] 情感分析器未配置，尝试从 service_context 获取")

            service_context = (config if config else {}).get("configurable", {}).get("service_context")

            if service_context and hasattr(service_context, "emotion_analyzer"):
                emotion_analyzer = service_context.emotion_analyzer
            else:
                logger.debug(f"[{session_id}] [情感节点] 无情感分析器，使用默认情感")
                return {"emotion": "neutral"}

        logger.debug(f"[{session_id}] [情感节点] 调用情感分析器...")

        result = emotion_analyzer.extract(response_text)
        primary_emotion = result.primary
        confidence = result.confidence

        logger.info(f"[{session_id}] [情感节点] 分析结果: {primary_emotion} (置信度: {confidence:.2f})")

        return {"emotion": primary_emotion}

    except Exception as e:
        logger.error(f"[{session_id}] [情感节点] 分析失败: {e}")
        return {"emotion": "neutral"}
