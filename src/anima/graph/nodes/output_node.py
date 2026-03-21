"""
输出分发节点

负责：
1. 接收最终结果 (response_text, tts_audio, emotion)
2. 通过 Socket.IO 推送到前端
3. 将对话存储到记忆系统

Socket.IO 事件:
- "sentence": {text, seq, is_complete} -> 流式文本块
- "audio_with_expression": {audio_data, format, volumes} -> 语音播放 + Live2D 口型同步
- "control": {signal} -> 控制信号
"""

import base64
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime
import os

from ..state import AgentState
from ..config_store import get_socketio, get_service_context


async def output_node(
    state: AgentState,
    config: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    输出分发节点（替代 EventBus）

    Args:
        state: 当前状态
        config: LangGraph 传入的运行时配置（自动注入）

    Returns:
        状态更新字典（通常为空）
    """
    session_id = state.get("session_id", "unknown")
    channel_id = state.get("channel_id")

    logger.info(f"[{session_id}] [输出节点] 开始分发...")

    # 从 ConfigStore 获取 Socket.IO 实例
    sio = get_socketio(session_id)

    if not sio:
        logger.error(f"[{session_id}] [输出节点] Socket.IO 未配置")
        return {"error": "Socket.IO 未配置"}

    # 确定目标客户端
    to = channel_id or session_id

    # ========================================
    # Phase 5: 存储对话到记忆系统
    # ========================================
    await _store_conversation_to_memory(
        state=state,
        config=config,
    )

    # ========================================
    # 发送文本回复（使用 sentence 事件）
    # ========================================
    response_text = state.get("response_text", "")

    if response_text:
        # 第一步：发送文本内容（seq=0）
        await sio.emit(
            "sentence",
            {
                "text": response_text,
                "seq": 0,
            },
            to=to,
        )
        logger.info(f"[{session_id}] [输出节点] ✅ 已发送文本回复")

        # 第二步：发送流结束标记（空文本）
        await sio.emit(
            "sentence",
            {
                "text": "",
                "is_complete": True,
            },
            to=to,
        )
        logger.debug(f"[{session_id}] [输出节点] ✅ 已发送流结束标记")
    else:
        logger.debug(f"[{session_id}] [输出节点] 无文本回复")

    # ========================================
    # 发送音频数据 + 口型同步
    # ========================================
    tts_audio = state.get("tts_audio")

    if tts_audio:
        try:
            # 处理音频数据
            audio_data = None
            format = "mp3"

            if isinstance(tts_audio, bytes):
                # 直接使用 bytes 数据
                audio_data = base64.b64encode(tts_audio).decode("utf-8")
            elif isinstance(tts_audio, str):
                # 读取文件并转换为 base64
                if os.path.exists(tts_audio):
                    with open(tts_audio, "rb") as f:
                        audio_data = base64.b64encode(f.read()).decode("utf-8")
                else:
                    logger.warning(f"[{session_id}] [输出节点] 音频文件不存在: {tts_audio}")
            else:
                logger.warning(f"[{session_id}] [输出节点] 未知音频类型: {type(tts_audio)}")

            if audio_data:
                await sio.emit(
                    "audio_with_expression",
                    {
                        "audio_data": audio_data,
                        "format": format,
                    },
                    to=to,
                )
                logger.info(f"[{session_id}] [输出节点] ✅ 已发送音频数据 (base64: {len(audio_data)} chars)")
            else:
                logger.warning(f"[{session_id}] [输出节点] 音频数据为空")

        except Exception as e:
            logger.error(f"[{session_id}] [输出节点] 音频处理失败: {e}")
    else:
        logger.debug(f"[{session_id}] [输出节点] 无音频数据")

    # ========================================
    # 返回空更新（输出节点不修改状态）
    # ========================================
    logger.info(f"[{session_id}] [输出节点] 分发完成")
    return {}


# ========================================
# Phase 5: 记忆存储相关函数
# ========================================

async def _store_conversation_to_memory(
    state: AgentState,
    config: Dict[str, Any],
) -> None:
    """Phase 5: 将本轮对话存储到记忆系统"""
    session_id = state.get("session_id", "unknown")

    try:
        service_context = get_service_context(session_id)
        if not service_context:
            return

        memory_system = service_context.memory_system
        if not memory_system:
            return

        user_text = state.get("user_text", "")
        response_text = state.get("response_text", "")

        if not user_text or not response_text:
            return

        emotion = state.get("emotion")
        emotions = [emotion] if emotion else []
        metadata = state.get("metadata", {})

        from ...memory.memory_turn import MemoryTurn

        turn = MemoryTurn(
            turn_id=f"{session_id}_{int(datetime.now().timestamp())}",
            session_id=session_id,
            timestamp=datetime.now(),
            user_input=user_text,
            agent_response=response_text,
            emotions=emotions,
            metadata=metadata,
        )

        await memory_system.store_turn(turn)
        logger.debug(f"[{session_id}] [输出节点] 已存储对话到记忆系统")

    except Exception as e:
        logger.warning(f"[{session_id}] [输出节点] 记忆存储失败: {e}")
