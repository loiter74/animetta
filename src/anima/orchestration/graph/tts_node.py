"""TTS 节点 - 文本转语音"""

from typing import Dict, Any, Optional
from loguru import logger
from langgraph.types import RunnableConfig

from .state import AgentState


def _get_service_context(config: Optional[RunnableConfig]) -> Optional[Any]:
    """从 LangGraph config 获取 service_context"""
    if config:
        return config.get("configurable", {}).get("service_context")
    return None


async def tts_node(
    state: AgentState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    TTS 语音合成节点

    输入: state["response_text"]
    输出: state["tts_audio"] (bytes or str)
    """
    session_id = state.get("session_id", "unknown")
    response_text = state.get("response_text", "")

    logger.info(f"[{session_id}] [TTS节点] 开始处理...")

    if not response_text:
        logger.warning(f"[{session_id}] [TTS节点] 无回复文本，跳过")
        return {"tts_audio": None}

    service_context = _get_service_context(config)
    if not service_context:
        logger.error(f"[{session_id}] [TTS节点] service_context 未配置")
        return {"error": "service_context 未配置", "tts_audio": None}

    tts_engine = service_context.tts_engine
    if not tts_engine:
        logger.warning(f"[{session_id}] [TTS节点] TTS 引擎未初始化，跳过")
        return {"tts_audio": None}

    logger.debug(f"[{session_id}] [TTS节点] 文本长度: {len(response_text)} 字符")

    audio = await tts_engine.synthesize(response_text)

    if isinstance(audio, bytes):
        logger.info(f"[{session_id}] [TTS节点] 音频数据: {len(audio)} bytes")
    elif isinstance(audio, str):
        logger.info(f"[{session_id}] [TTS节点] 音频文件: {audio}")

    return {"tts_audio": audio}
