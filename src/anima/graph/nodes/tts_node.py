"""
TTS (语音合成) 节点

负责：
1. 接收 LLM 回复文本 (state["response_text"])
2. 调用现有 TTS 服务 (service_context.tts_engine)
3. 将合成音频写入 state["tts_audio"]
"""

from typing import Dict, Any, Optional
from loguru import logger

from ..state import AgentState
from ..config_store import get_service_context


async def tts_node(
    state: AgentState,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    语音合成节点

    输入: state["response_text"]
    输出: state["tts_audio"] (bytes or str)

    Args:
        state: 当前状态
        config: LangGraph 传入的运行时配置（自动注入）

    Returns:
        状态更新字典
    """
    session_id = state.get("session_id", "unknown")
    response_text = state.get("response_text", "")

    logger.info(f"[{session_id}] [TTS节点] 开始处理...")

    # ========================================
    # 验证输入
    # ========================================
    if not response_text:
        logger.warning(f"[{session_id}] [TTS节点] 无回复文本，跳过")
        return {
            "tts_audio": None,
        }

    # 从 ConfigStore 获取 service_context
    service_context = get_service_context(session_id)

    if not service_context:
        logger.error(f"[{session_id}] [TTS节点] service_context 未配置")
        return {
            "error": "service_context 未配置",
            "tts_audio": None,
        }

    tts_engine = service_context.tts_engine

    if not tts_engine:
        logger.warning(f"[{session_id}] [TTS节点] TTS 引擎未初始化，跳过")
        # TTS 可选，不是必需服务
        return {
            "tts_audio": None,
        }

    # ========================================
    # 调用 TTS 服务
    # ========================================
    logger.debug(f"[{session_id}] [TTS节点] 调用 TTS 服务...")
    logger.debug(f"[{session_id}] [TTS节点] 文本长度: {len(response_text)} 字符")

    audio = await tts_engine.synthesize(response_text)

    # 判断返回类型
    if isinstance(audio, bytes):
        logger.info(f"[{session_id}] [TTS节点] 音频数据: {len(audio)} bytes")
    elif isinstance(audio, str):
        logger.info(f"[{session_id}] [TTS节点] 音频文件: {audio}")
    else:
        logger.warning(f"[{session_id}] [TTS节点] 未知音频类型: {type(audio)}")

    # ========================================
    # 返回状态更新
    # ========================================
    return {
        "tts_audio": audio,
    }
