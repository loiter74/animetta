"""Output distribution node - Socket.IO push + memory storage"""

import asyncio
import base64
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime
import os
from functools import partial
from langgraph.types import RunnableConfig

from .state import AgentState


def _get_from_config(config: Optional[RunnableConfig], key: str) -> Optional[Any]:
    """Get value from LangGraph config"""
    if config:
        return config.get("configurable", {}).get(key)
    return None


async def output_node(
    state: AgentState,
    config: Optional[RunnableConfig] = None,
) -> Dict[str, Any]:
    """
    Output distribution node

    Push text and audio to frontend via Socket.IO, store conversation in memory system
    """
    session_id = state.get("session_id", "unknown")
    channel_id = state.get("channel_id")

    logger.info(f"[{session_id}] [OutputNode] Starting distribution...")

    sio = _get_from_config(config, "socketio")
    if not sio:
        logger.error(f"[{session_id}] [OutputNode] Socket.IO not configured")
        return {"error": "Socket.IO not configured"}

    to = channel_id or session_id

    # Send conversation-start signal
    await sio.emit("control", {"signal": "conversation-start"}, to=to)

    # Store conversation in memory system
    await _store_conversation_to_memory(state=state, config=config)

    # Send text response
    response_text = state.get("response_text", "")
    if response_text:
        await sio.emit("sentence", {"text": response_text, "seq": 0}, to=to)
        logger.info(f"[{session_id}] [OutputNode] ✅ Sent text response")

        await sio.emit("sentence", {"text": "", "is_complete": True}, to=to)
        logger.debug(f"[{session_id}] [OutputNode] ✅ Sent stream end marker")

    # Send emotion event — also send motion command to frontend
    emotion = state.get("emotion")
    if emotion:
        await sio.emit("expression", {"emotion": emotion}, to=to)
        logger.debug(f"[{session_id}] [OutputNode] Sent emotion: {emotion}")

        # Map emotion to Live2D motion command (for models like Hiyori without expression files)
        EMOTION_MOTION_MAP = {
            "happy": 3,
            "sad": 1,
            "angry": 2,
            "surprised": 4,
            "neutral": 0,
            "thinking": 5,
        }
        motion_idx = EMOTION_MOTION_MAP.get(emotion)
        if motion_idx is not None:
            await sio.emit("live2d.action", {
                "type": "motion",
                "group": "Idle",
                "index": motion_idx,
            }, to=to)
            logger.debug(f"[{session_id}] [OutputNode] Sent Live2D motion: Idle[{motion_idx}] for {emotion}")

    # Send audio data (with parallel processing for independent operations)
    tts_audio = state.get("tts_audio")
    if tts_audio:
        try:
            audio_data = None
            format = "mp3"
            volumes = []

            if isinstance(tts_audio, str) and os.path.exists(tts_audio):
                # ── Parallel: trim_silence, compute_volumes, read_file are independent ──
                loop = asyncio.get_running_loop()
                (
                    trimmed_path,
                    raw_bytes,
                    vol_result,
                ) = await asyncio.gather(
                    loop.run_in_executor(None, _trim_leading_silence, tts_audio),
                    loop.run_in_executor(None, partial(_read_file_bytes, tts_audio)),
                    loop.run_in_executor(None, _compute_volumes, tts_audio),
                )

                audio_source = trimmed_path or tts_audio
                ext = os.path.splitext(audio_source)[1].lower()
                format = ext.lstrip('.') if ext else "mp3"
                audio_data = base64.b64encode(raw_bytes).decode("utf-8")
                volumes = vol_result or []

            elif isinstance(tts_audio, bytes):
                audio_data = base64.b64encode(tts_audio).decode("utf-8")
                volumes = []

            if audio_data:
                payload = {"audio_data": audio_data, "format": format}
                if volumes:
                    payload["volumes"] = volumes
                await sio.emit("audio_with_expression", payload, to=to)
                logger.info(f"[{session_id}] [OutputNode] ✅ Sent audio data (volumes: {len(volumes)} samples)")

        except Exception as e:
            logger.error(f"[{session_id}] [OutputNode] Audio processing failed: {e}")

    # Send conversation-end signal
    await sio.emit("control", {"signal": "conversation-end"}, to=to)

    logger.info(f"[{session_id}] [OutputNode] Distribution complete")
    return {}


def _read_file_bytes(path: str) -> bytes:
    """Read a file as bytes (runs in thread pool)."""
    with open(path, "rb") as f:
        return f.read()


def _trim_leading_silence(audio_path: str) -> str | None:
    """Trim leading silence from audio and return path to trimmed file.

    This ensures audio playback and lip sync both start when speech begins.
    Returns None if no trimming was needed.
    """
    try:
        from pydub import AudioSegment
        import tempfile

        audio = AudioSegment.from_file(audio_path).set_channels(1)
        threshold = -45  # dBFS
        trim_ms = 0
        for start_ms in range(0, min(500, len(audio)), 10):  # check first 500ms max
            seg = audio[start_ms:start_ms + 10]
            if seg.dBFS > threshold:
                trim_ms = start_ms
                break

        if trim_ms > 50:  # only trim if more than 50ms of silence
            trimmed = audio[trim_ms:]
            tmp = tempfile.mktemp(suffix=".wav")
            trimmed.export(tmp, format="wav")
            logger.debug(f"[output_node] Trimmed {trim_ms}ms leading silence from audio")
            return tmp
        return None
    except Exception as e:
        logger.debug(f"[output_node] Silence trimming skipped: {e}")
        return None


def _compute_volumes(audio_path: str) -> list:
    """Compute the volume envelope of an audio file for lip sync.

    Uses peak amplitude WITHOUT global normalization, so a loud sound
    at the start doesn't suppress the rest of the mouth movement.
    """
    try:
        from anima.avatar.analyzers.audio import AudioAnalyzer
        analyzer = AudioAnalyzer()
        volumes = analyzer.compute_volume_envelope(
            audio_path, normalize=False, gain=3.5, use_peak=True)

        # Clamp to [0, 1] after gain
        if volumes:
            volumes = [min(1.0, v) for v in volumes]
            non_zero = sum(1 for v in volumes if v > 0.01)
            logger.info(f"[output_node] Volumes: {len(volumes)} frames, "
                        f"{non_zero} non-zero, "
                        f"range=[{min(volumes):.3f}, {max(volumes):.3f}], "
                        f"first_10={[round(v,2) for v in volumes[:10]]}")

        return volumes
    except Exception as e:
        logger.debug(f"[output_node] Computing volumes failed: {e}")
        return []


async def _store_conversation_to_memory(
    state: AgentState,
    config: Optional[RunnableConfig],
) -> None:
    """Store the current conversation turn into the memory system"""
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
        logger.debug(f"[{session_id}] [OutputNode] Stored conversation in memory system")

    except Exception as e:
        logger.warning(f"[{session_id}] [OutputNode] Memory storage failed: {e}")
