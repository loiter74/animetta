"""
情感分析节点

负责：
1. 接收 LLM 回复文本 (state["response_text"])
2. 调用现有情感分析器 (avatar.emotion_analyzer)
3. 将情感标签写入 state["emotion"]
"""

from typing import Dict, Any, Optional
from loguru import logger

from ..state import AgentState
from ..config_store import get_service_context


async def emotion_node(
    state: AgentState,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    情感分析节点

    输入: state["response_text"]
    输出: state["emotion"] (str: "happy", "sad", "angry", "neutral" 等)

    Args:
        state: 当前状态
        config: LangGraph 传入的运行时配置（自动注入）

    Returns:
        状态更新字典
    """
    session_id = state.get("session_id", "unknown")
    response_text = state.get("response_text", "")

    logger.info(f"[{session_id}] [情感节点] 开始分析...")

    # ========================================
    # 验证输入
    # ========================================
    if not response_text:
        logger.warning(f"[{session_id}] [情感节点] 无回复文本，使用默认情感")
        return {
            "emotion": "neutral",
        }

    # config 由 LangGraph 自动注入
    if config is None:
        config = state.get("_config", {})

    try:
        # ========================================
        # 获取情感分析器
        # ========================================
        emotion_analyzer = (config if config else {}).get("configurable", {}).get("emotion_analyzer")

        if not emotion_analyzer:
            logger.debug(f"[{session_id}] [情感节点] 情感分析器未配置，尝试从 service_context 获取")

            # 尝试从 service_context 获取
            service_context = (config if config else {}).get("configurable", {}).get("service_context")

            if service_context and hasattr(service_context, "emotion_analyzer"):
                emotion_analyzer = service_context.emotion_analyzer
            else:
                # 没有情感分析器，使用默认值
                logger.debug(f"[{session_id}] [情感节点] 无情感分析器，使用默认情感")
                return {
                    "emotion": "neutral",
                }

        # ========================================
        # 调用情感分析
        # ========================================
        logger.debug(f"[{session_id}] [情感节点] 调用情感分析器...")

        # 调用情感分析器
        result = emotion_analyzer.extract(response_text)

        # 获取主要情感
        primary_emotion = result.primary
        confidence = result.confidence

        logger.info(f"[{session_id}] [情感节点] 分析结果: {primary_emotion} (置信度: {confidence:.2f})")

        # ========================================
        # 返回状态更新
        # ========================================
        return {
            "emotion": primary_emotion,
        }

    except Exception as e:
        logger.error(f"[{session_id}] [情感节点] 分析失败: {e}")
        # 情感分析失败不应该阻断流程，使用默认值
        return {
            "emotion": "neutral",
        }


def _normalize_emotion(emotion: str) -> str:
    """
    标准化情感标签

    将不同的情感标签映射到 Live2D 支持的标准标签。

    Args:
        emotion: 原始情感标签

    Returns:
        str: 标准化后的情感标签
    """
    # 标准情感标签
    standard_emotions = {
        "happy": ["happy", "joy", "excited", "glad", "pleased"],
        "sad": ["sad", "unhappy", "down", "depressed"],
        "angry": ["angry", "mad", "furious", "annoyed"],
        "surprised": ["surprised", "shocked", "amazed"],
        "thinking": ["thinking", "thoughtful", "pondering"],
        "neutral": ["neutral", "calm", "peaceful"],
    }

    emotion_lower = emotion.lower()

    for standard, variants in standard_emotions.items():
        if emotion_lower in variants:
            return standard

    return "neutral"
