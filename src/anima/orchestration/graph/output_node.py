"""输出分发节点 - Socket.IO 推送 + 记忆存储"""

import base64
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime
import os
from langgraph.types import RunnableConfig

from .state import AgentState


def _get_from_config(config: Optional[RunnableConfig], key: str) -> Optional[Any]:
    """从 LangGraph config 获取值"""
    if config:
        return config.get("configurable", {}).get(key)
    return None


async def output_node(
    state: AgentState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    输出分发节点

    通过 Socket.IO 推送文本和音频到前端，存储对话到记忆系统
    """
    session_id = state.get("session_id", "unknown")
    channel_id = state.get("channel_id")

    logger.info(f"[{session_id}] [输出节点] 开始分发...")

    sio = _get_from_config(config, "socketio")
    if not sio:
        logger.error(f"[{session_id}] [输出节点] Socket.IO 未配置")
        return {"error": "Socket.IO 未配置"}

    to = channel_id or session_id

    # 发送 conversation-start 信号
    await sio.emit("control", {"signal": "conversation-start"}, to=to)

    # 存储对话到记忆系统
    await _store_conversation_to_memory(state=state, config=config)

    # 发送文本回复
    response_text = state.get("response_text", "")
    if response_text:
        await sio.emit("sentence", {"text": response_text, "seq": 0}, to=to)
        logger.info(f"[{session_id}] [输出节点] ✅ 已发送文本回复")

        await sio.emit("sentence", {"text": "", "is_complete": True}, to=to)
        logger.debug(f"[{session_id}] [输出节点] ✅ 已发送流结束标记")

    # 发送表情事件
    emotion = state.get("emotion")
    if emotion:
        await sio.emit("expression", {"emotion": emotion}, to=to)
        logger.debug(f"[{session_id}] [输出节点] 已发送表情: {emotion}")

    # 发送音频数据
    tts_audio = state.get("tts_audio")
    if tts_audio:
        try:
            audio_data = None
            format = "mp3"
            volumes = []

            if isinstance(tts_audio, bytes):
                audio_data = base64.b64encode(tts_audio).decode("utf-8")
            elif isinstance(tts_audio, str):
                if os.path.exists(tts_audio):
                    with open(tts_audio, "rb") as f:
                        audio_data = base64.b64encode(f.read()).decode("utf-8")

                    # 计算音量包络用于口型同步
                    volumes = _compute_volumes(tts_audio)

            if audio_data:
                payload = {"audio_data": audio_data, "format": format}
                if volumes:
                    payload["volumes"] = volumes
                await sio.emit("audio_with_expression", payload, to=to)
                logger.info(f"[{session_id}] [输出节点] ✅ 已发送音频数据 (volumes: {len(volumes)} samples)")

        except Exception as e:
            logger.error(f"[{session_id}] [输出节点] 音频处理失败: {e}")

    # 发送 conversation-end 信号
    await sio.emit("control", {"signal": "conversation-end"}, to=to)

    logger.info(f"[{session_id}] [输出节点] 分发完成")
    return {}


def _compute_volumes(audio_path: str) -> list:
    """计算音频文件的音量包络用于口型同步"""
    try:
        from anima.avatar.analyzers.audio import AudioAnalyzer
        analyzer = AudioAnalyzer()
        return analyzer.compute_volume_envelope(audio_path, normalize=True, gain=1.8)
    except Exception as e:
        logger.debug(f"[output_node] 计算 volumes 失败: {e}")
        return []


async def _store_conversation_to_memory(
    state: AgentState,
    config: Optional[RunnableConfig],
) -> None:
    """将本轮对话存储到记忆系统"""
    session_id = state.get("session_id", "unknown")

    try:
        service_context = _get_from_config(config, "service_context")
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

        from ...memory.models.turns import MemoryTurn

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
