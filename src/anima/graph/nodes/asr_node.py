"""
ASR (语音识别) 节点

负责：
1. 接收音频数据 (state["raw_audio"])
2. 调用现有 ASR 服务 (service_context.asr_engine)
3. 将识别结果写入 state["user_text"]
"""

from typing import Dict, Any, Optional
from loguru import logger
from langchain_core.messages import HumanMessage

from ..state import AgentState
from ..config_store import get_service_context


async def asr_node(
    state: AgentState,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    语音识别节点

    输入: state["raw_audio"] (bytes)
    输出: state["user_text"] (str), state["messages"] (追加用户消息)

    Args:
        state: 当前状态
        config: LangGraph 传入的运行时配置（自动注入）

    Returns:
        状态更新字典
    """
    session_id = state.get("session_id", "unknown")
    raw_audio = state.get("raw_audio")

    logger.info(f"[{session_id}] [ASR节点] 开始处理音频...")

    # ========================================
    # 验证输入
    # ========================================
    if not raw_audio:
        logger.warning(f"[{session_id}] [ASR节点] 无音频数据，跳过")
        return {
            "error": "无音频数据",
            "user_text": "",
        }

    # 从 ConfigStore 获取 service_context
    service_context = get_service_context(session_id)

    if not service_context:
        logger.error(f"[{session_id}] [ASR节点] service_context 未配置")
        return {
            "error": "service_context 未配置",
            "user_text": "",
        }

    asr_engine = service_context.asr_engine

    if not asr_engine:
        logger.error(f"[{session_id}] [ASR节点] ASR 引擎未初始化")
        return {
            "error": "ASR 引擎未初始化",
            "user_text": "",
        }

    # ========================================
    # 调用 ASR 服务
    # ========================================
    logger.debug(f"[{session_id}] [ASR节点] 调用 ASR 服务...")
    text = await asr_engine.transcribe(raw_audio)

    logger.info(f"[{session_id}] [ASR节点] 识别结果: {text[:50]}...")

    # ========================================
    # 创建用户消息
    # ========================================
    user_id = state.get("user_id")
    user_name = state.get("user_name")
    channel_id = state.get("channel_id")

    # 构建消息内容
    content = text
    if user_name:
        content = f"[{user_name}]: {text}"

    message = HumanMessage(
        content=content,
        name=user_id or "user",
    )

    # ========================================
    # 返回状态更新
    # ========================================
    return {
        "user_text": text,
        "messages": [message],
    }
