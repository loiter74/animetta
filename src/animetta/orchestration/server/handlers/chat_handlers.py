"""
Chat/conversation handlers — text input, audio, history management.

Handles user text/audio input, VAD processing, interrupt signals,
and conversation history operations.
"""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from socketio import AsyncServer

    from ..session import SessionManager
    from .base_handler import BaseSocketHandler


class ChatHandlers:
    """Chat and conversation event handlers.

    Receives sio, session_manager, and a reference to BaseSocketHandler
    for shared utilities like _get_or_create_orchestrator.
    """

    def __init__(
        self,
        sio: "AsyncServer",
        session_manager: "SessionManager",
        admin: "BaseSocketHandler",
    ):
        self.sio = sio
        self.session_manager = session_manager
        self.admin = admin
        self._raw_audio_first_sids: set = set()

    # ── Text input ────────────────────────────────────────────────────

    async def on_text_input(self, sid: str, data: dict) -> None:
        """Handle text input."""
        text = data.get("text", "")
        logger.info(f"[{sid}] Received text input: {text}")

        if not text:
            return

        # OTel metrics: session messages counter
        try:

            sm = get_session_messages()
            if sm is not None:
                sm.add(1)
        except Exception as e:
            logger.debug(f"[ChatHandlers] OTel session_messages metric failed: {e}")

        try:
            orchestrator = await self.admin._get_or_create_orchestrator(sid)
            await orchestrator.process_text(
                text=text,
                user_id=data.get("user_id", "user"),
                user_name=data.get("from_name", "User"),
                channel_id=sid,
            )
        except Exception as e:
            logger.error(f"[{sid}] Error processing text input: {e}")

            # OTel metrics: websocket errors counter
            try:

                we = get_websocket_errors()
                if we is not None:
                    we.add(1)
            except Exception as e:
                logger.debug(f"[ChatHandlers] OTel websocket_errors metric failed: {e}")
            await self.sio.emit(
                "error", {"type": "error", "message": str(e)}, to=sid
            )

    # ── Audio / VAD ───────────────────────────────────────────────────

    async def on_raw_audio_data(self, sid: str, data: dict) -> None:
        """Handle raw audio data for VAD detection."""
        audio_chunk = data.get("audio", [])

        if not audio_chunk:
            logger.debug(f"[{sid}] Received empty audio data")
            return

        if sid not in self._raw_audio_first_sids:
            self._raw_audio_first_sids.add(sid)
            logger.info(f"[{sid}] [RAW_AUDIO] Starting to receive audio data")

        try:
            await self.admin._get_or_create_orchestrator(sid)

            processor = self.session_manager.get_audio_processor(sid)
            if processor:
                await processor.process_chunk(audio_chunk)
            else:
                logger.error(f"[{sid}] Audio processor not created")

        except Exception as e:
            logger.error(f"[{sid}] VAD processing error: {e}", exc_info=True)

    async def on_mic_audio_end(self, sid: str, data: dict) -> None:
        """Audio input end event."""
        logger.info(f"[{sid}] Audio input ended")

        try:
            processor = self.session_manager.get_audio_processor(sid)
            if processor:
                await processor.process_end()

        except Exception as e:
            logger.error(f"[{sid}] Error processing audio: {e}")
            await self.sio.emit(
                "error", {"type": "error", "message": str(e)}, to=sid
            )

    # ── Interrupt ─────────────────────────────────────────────────────

    async def on_interrupt_signal(self, sid: str, data: dict) -> None:
        """Interrupt signal - stop LLM generation and audio playback."""
        heard_response = data.get("text", "")
        logger.info(
            f"[{sid}] Received interrupt signal, "
            f"heard response: {heard_response[:50] if heard_response else '(empty)'}..."
        )


        interrupt_handler = get_interrupt_handler()
        interrupt_handler.set_interrupt(sid)

        await self.sio.emit("stop_audio", {}, to=sid)

        await self.sio.emit(
            "control", {"type": "control", "text": "interrupted"}, to=sid
        )

    # ── History ────────────────────────────────────────────────────────

    async def on_fetch_history_list(self, sid: str, data: dict) -> None:
        """Fetch chat history list."""
        logger.info(f"[{sid}] Requested chat history list")

    async def on_fetch_history(self, sid: str, data: dict) -> None:
        """Fetch specific history record."""
        history_uid = data.get("history_uid")
        logger.info(f"[{sid}] Requested history: {history_uid}")
        messages = []

        await self.sio.emit(
            "history-data",
            {"type": "history-data", "messages": messages},
            to=sid,
        )

    async def on_clear_history(self, sid: str, data: dict) -> None:
        """Clear conversation history."""
        logger.info(f"[{sid}] Clearing conversation history")

        ctx = self.session_manager.get_context(sid)
        if ctx and ctx.llm_engine:
            ctx.llm_engine.clear_history()
            logger.info(f"[{sid}] Conversation history cleared")

            await self.sio.emit(
                "history-cleared", {"type": "history-cleared"}, to=sid
            )

    async def on_create_new_history(self, sid: str, data: dict) -> None:
        """Create new conversation history."""
        logger.info(f"[{sid}] Creating new conversation history")

        await self.sio.emit(
            "new-history-created",
            {"type": "new-history-created", "history_uid": "new_history_001"},
            to=sid,
        )
