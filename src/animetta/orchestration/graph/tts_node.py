"""TTS node - text to speech"""

import asyncio
import time
from typing import Any

from langchain_core.runnables import RunnableConfig
from loguru import logger

from animetta.avatar.performance import validated_performance_payload
from animetta.orchestration.chat_contracts import ChatIdentity, ChatTransportMode
from animetta.orchestration.chat_delivery import ChatDelivery, resolve_delivery_target
from animetta.runtime.readiness import resolve_service_identity, unwrap_tracing_proxy
from animetta.services.dialogue.response_processing import clean_text_for_tts as _clean_text_for_tts
from animetta.services.tts.emotion_instructions import build_emotion_instruction
from animetta.services.tts.remote_tts import RemoteTTSError
from animetta.services.tts.streaming import StreamEvent, synthesize_stream

from .interrupt_handler import get_interrupt_handler
from .media_status import MediaStatus
from .node_error import log_node_error
from .state import AgentState, log_timing


def _get_service_context(config: RunnableConfig | None) -> Any | None:
    """Get service_context from LangGraph config"""
    if config:
        return config.get("configurable", {}).get("service_context")
    return None


def _resolve_provider_identity(
    service_context: Any,
    tts_engine: Any,
) -> tuple[str, str | None, bool]:
    """Return bounded actual provider metadata and config-match status."""
    runtime_config = getattr(service_context, "config", None)
    providers = getattr(runtime_config, "providers", None)
    configured = providers.get("tts") if hasattr(providers, "get") else None
    if configured is not None:
        identity = resolve_service_identity("tts", tts_engine, configured)
        if identity is None:
            return "unknown", None, False
        expected = configured.public_identity()
        matches = all(
            identity.get(field) == expected.get(field)
            for field in ("type", "provider", "model", "voice")
            if expected.get(field) is not None
        )
        provider = identity.get("provider") or identity.get("type") or "unknown"
        return provider, identity.get("type"), matches

    target = unwrap_tracing_proxy(tts_engine)
    if target is None:
        return "unknown", None, False
    class_name = type(target).__name__
    return class_name, None, True


def _stream_delivery(
    state: AgentState,
    config: RunnableConfig | None,
) -> tuple[ChatDelivery | None, str | None]:
    configurable = config.get("configurable", {}) if config else {}
    sio = configurable.get("socketio")
    if sio is None:
        return None, ""
    identity = ChatIdentity(
        message_id=state["message_id"],
        conversation_id=state["conversation_id"],
        task_id=state["task_id"],
        turn_id=state["turn_id"],
    )
    mode = ChatTransportMode(
        state.get("metadata", {}).get("transport_mode", ChatTransportMode.CANONICAL.value)
    )
    recorder = configurable.get("observation_recorder")
    delivery = (
        ChatDelivery(sio, identity, mode, recorder=recorder)
        if recorder is not None
        else ChatDelivery(sio, identity, mode)
    )
    return delivery, resolve_delivery_target(state)


async def _synthesize_streaming(
    *,
    state: AgentState,
    config: RunnableConfig | None,
    tts_engine: Any,
    clean_text: str,
    emotion: str,
    instruction: str,
    timeout_seconds: float,
    provider: str,
    started: float,
) -> dict[str, Any]:
    delivery, to = _stream_delivery(state, config)
    if delivery is None:
        raise RuntimeError("Socket.IO is required for progressive TTS")
    performance = validated_performance_payload(state.get("performance_plan"))

    async def emit(event: StreamEvent, payload: dict[str, Any]) -> None:
        assert delivery is not None
        await delivery.emit_tts_stream(
            event, payload, to=to, emotion=emotion, performance=performance
        )

    result = await synthesize_stream(
        tts_engine,
        clean_text,
        synthesis_kwargs={"emotion": emotion, "instruction": instruction},
        interrupt_signal=get_interrupt_handler().get_signal(state["session_id"]),
        emit=emit,
        timeout_seconds=timeout_seconds,
        started=started,
    )
    if result.interrupted:
        log_timing(state, "tts.synthesize", result.duration_ms, "skipped:interrupted")
        return {
            "tts_audio": None,
            "media_status": MediaStatus("skipped", "interrupted", provider, False),
            "metadata": {
                **state.get("metadata", {}),
                "tts_provider": provider,
                "media_status": "skipped",
                "interruption_reason": "interrupted",
                "audio_streamed": result.streamed,
                **({"audio_stream_id": result.stream_id} if result.streamed else {}),
            },
        }
    actual_provider = _actual_tts_provider(tts_engine, provider)
    log_timing(state, "tts.synthesize", result.duration_ms, "ready:streamed")
    return {
        "tts_audio": None,
        "media_status": MediaStatus("ready", provider=actual_provider),
        "metadata": {
            **state.get("metadata", {}),
            "tts_provider": actual_provider,
            "tts_first_audio_ms": result.first_audio_ms,
            "tts_rtf": result.rtf,
            "media_status": "ready",
            "audio_streamed": True,
            "audio_stream_id": result.stream_id,
        },
    }


def _actual_tts_provider(tts_engine: Any, default: str) -> str:
    value = getattr(tts_engine, "actual_provider", None)
    return value if isinstance(value, str) and value else default


async def tts_node(
    state: AgentState,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
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
        return {"tts_audio": None, "media_status": MediaStatus("skipped", "no_text")}

    service_context = _get_service_context(config)
    if not service_context:
        logger.error(f"[{session_id}] [TTSNode] service_context not configured")
        return {
            "error": "service_context not configured",
            "tts_audio": None,
            "media_status": MediaStatus("degraded", "service_unavailable", retryable=True),
        }

    tts_engine = service_context.tts_engine
    if not tts_engine:
        logger.warning(f"[{session_id}] [TTSNode] TTS engine not initialized, skipping")
        return {
            "tts_audio": None,
            "media_status": MediaStatus("degraded", "provider_unavailable", retryable=True),
        }

    system = getattr(getattr(service_context, "config", None), "system", None)
    golden = getattr(system, "runtime_profile", None) in {
        "smoke",
        "production",
        "golden",
    }
    provider, provider_type, identity_matches = _resolve_provider_identity(
        service_context,
        tts_engine,
    )
    if golden and (provider_type == "mock" or provider == "mock"):
        return {
            "tts_audio": None,
            "media_status": MediaStatus("degraded", "mock_forbidden", provider, False),
        }
    if golden and not identity_matches:
        return {
            "tts_audio": None,
            "media_status": MediaStatus(
                "degraded",
                "identity_mismatch",
                provider,
                False,
            ),
        }

    # Strip emoji and emotion tags before TTS so the voice doesn't read them aloud
    clean_text = _clean_text_for_tts(response_text)
    emotion = str(state.get("emotion") or "neutral")
    synthesis_kwargs: dict[str, Any] = {}
    if getattr(tts_engine, "supports_emotion_instructions", False) is True:
        synthesis_kwargs = {
            "emotion": emotion,
            "instruction": build_emotion_instruction(emotion),
        }
    logger.debug(
        f"[{session_id}] [TTSNode] Text length: {len(response_text)} chars → {len(clean_text)} chars (cleaned)"
    )

    try:
        started = time.perf_counter()
        timeout_seconds = (
            float(getattr(system, "golden_tts_timeout_seconds", 20.0)) if golden else 300.0
        )
        if getattr(tts_engine, "supports_streaming", False) is True:
            return await _synthesize_streaming(
                state=state,
                config=config,
                tts_engine=tts_engine,
                clean_text=clean_text,
                emotion=emotion,
                instruction=build_emotion_instruction(emotion),
                timeout_seconds=timeout_seconds,
                provider=provider,
                started=started,
            )
        audio = await asyncio.wait_for(
            tts_engine.synthesize(clean_text, **synthesis_kwargs), timeout=timeout_seconds
        )
    except TimeoutError:
        log_timing(
            state, "tts.synthesize", (time.perf_counter() - started) * 1000, "degraded:timeout"
        )
        logger.warning(f"[{session_id}] [TTSNode] TTS timed out")
        await log_node_error(session_id, "tts_node", "timeout", duration_ms=0)
        return {
            "tts_audio": None,
            "media_status": MediaStatus("degraded", "timeout", provider, True),
            "metadata": {
                **state.get("metadata", {}),
                "tts_provider": provider,
                "media_status": "degraded",
                "degradation_reason": "timeout",
            },
        }
    except RemoteTTSError as e:
        category = e.category
        log_timing(
            state,
            "tts.synthesize",
            (time.perf_counter() - started) * 1000,
            f"degraded:{category}",
        )
        logger.warning(
            "[{}] [TTSNode] Remote TTS degraded: category={}, retryable={}",
            session_id,
            category,
            e.retryable,
        )
        await log_node_error(session_id, "tts_node", category, duration_ms=0)
        return {
            "tts_audio": None,
            "media_status": MediaStatus(
                "degraded",
                category,
                provider,
                e.retryable,
            ),
            "metadata": {
                **state.get("metadata", {}),
                "tts_provider": provider,
                "media_status": "degraded",
                "degradation_reason": category,
            },
        }
    except Exception as e:
        log_timing(
            state,
            "tts.synthesize",
            (time.perf_counter() - started) * 1000,
            "degraded:provider_error",
        )
        logger.warning(
            "[{}] [TTSNode] TTS failed: error_type={}",
            session_id,
            type(e).__name__,
        )
        await log_node_error(session_id, "tts_node", "network_error", duration_ms=0)
        return {
            "tts_audio": None,
            "media_status": MediaStatus("degraded", "provider_error", provider, True),
            "metadata": {
                **state.get("metadata", {}),
                "tts_provider": provider,
                "media_status": "degraded",
                "degradation_reason": "provider_error",
            },
        }

    if not audio or not isinstance(audio, (bytes, str)):
        log_timing(
            state, "tts.synthesize", (time.perf_counter() - started) * 1000, "degraded:empty_audio"
        )
        return {
            "tts_audio": None,
            "media_status": MediaStatus("degraded", "empty_audio", provider, True),
            "metadata": {
                **state.get("metadata", {}),
                "tts_provider": provider,
                "media_status": "degraded",
                "degradation_reason": "empty_audio",
            },
        }

    if isinstance(audio, bytes):
        logger.info(f"[{session_id}] [TTSNode] Audio data: {len(audio)} bytes")
    elif isinstance(audio, str):
        logger.info(f"[{session_id}] [TTSNode] Audio file: {audio}")

    provider = _actual_tts_provider(tts_engine, provider)
    log_timing(state, "tts.synthesize", (time.perf_counter() - started) * 1000, "ready")
    return {
        "tts_audio": audio,
        "media_status": MediaStatus("ready", provider=provider),
        "metadata": {
            **state.get("metadata", {}),
            "tts_provider": provider,
            "media_status": "ready",
        },
    }
