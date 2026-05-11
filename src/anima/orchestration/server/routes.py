"""WebSocket route definitions - handle conversations using the LangGraph orchestrator"""

import json
import time
import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING
from loguru import logger

# Import audio helpers from output_node for danmaku audio broadcasting
from anima.orchestration.graph.output_node import _compute_volumes, _read_file_bytes
from anima.orchestration.graph.translation_state import translation_state

from .desktop import DesktopClientManager
from .live2d import Live2DManager

if TYPE_CHECKING:
    from .session import SessionManager
    from socketio import AsyncServer


class RouteHandlers:
    """Collection of route handlers"""

    def __init__(
        self,
        sio: "AsyncServer",
        session_manager: "SessionManager",
        desktop_manager: Optional[DesktopClientManager] = None,
        live2d_manager: Optional[Live2DManager] = None,
    ):
        self.sio = sio
        self.session_manager = session_manager
        self.desktop_manager = desktop_manager or DesktopClientManager()
        self.live2d_manager = live2d_manager or Live2DManager()

        self.global_config = None
        self.user_settings = None

        # Bilibili danmaku service (initialized via start_bilibili)
        self._bilibili_service = None
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

        self._setup_live2d_callback()

    def _setup_live2d_callback(self) -> None:
        """Set up Live2D action execution callback"""
        async def execute_action(action):
            await self.broadcast_to_desktop_clients("live2d", "live2d.action", {
                "action": action.action,
                "action_id": action.action_id
            })
        self.live2d_manager.set_execute_callback(execute_action)

    def set_global_config(self, config) -> None:
        """Set global config"""

    def set_user_settings(self, user_settings) -> None:
        """Set user settings"""
        self.user_settings = user_settings

    # ========================================
    # Bilibili Danmaku Integration
    # ========================================

    def start_bilibili(self, room_id: int, sessdata: str = "") -> None:
        """Start Bilibili danmaku service. Stops existing service if running."""
        from anima.services.live import BilibiliDanmakuService

        # Stop existing service if already running
        if self._bilibili_service is not None:
            self.stop_bilibili()

        self._main_loop = asyncio.get_running_loop()
        self._bilibili_service = BilibiliDanmakuService(
            room_id=room_id,
            sessdata=sessdata,
        )
        self._bilibili_service.set_callback(self._on_danmaku_from_thread)
        self._bilibili_service.set_status_callback(self._on_bilibili_status_from_thread)
        self._bilibili_service.start()

    def stop_bilibili(self) -> None:
        """Stop Bilibili danmaku service."""
        if self._bilibili_service:
            self._bilibili_service.stop()
            self._bilibili_service = None

    def _on_danmaku_from_thread(self, msg) -> None:
        """Called from Bilibili background thread; schedule on main event loop."""
        if self._main_loop and self._main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._process_danmaku(msg), self._main_loop
            )

    def _on_bilibili_status_from_thread(self, connected: bool, message: str) -> None:
        """Called from Bilibili background thread; schedule status emit on main loop."""
        if self._main_loop and self._main_loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._emit_bilibili_status(connected, message), self._main_loop
            )

    async def _emit_bilibili_status(self, connected: bool, message: str) -> None:
        """Emit Bilibili connection status to all clients."""
        await self.sio.emit('danmaku.status', {
            'connected': connected,
            'message': message,
        })

    async def _process_danmaku(self, msg) -> None:
        """
        Process a danmaku message in the main event loop.
        1. Emit raw danmaku event to frontend
        2. Process with AI via LangGraph orchestrator
        3. Broadcast text, audio, and AI reply events to ALL clients
        """
        # 1. Broadcast raw danmaku to all clients
        await self.sio.emit('danmaku', msg.to_dict())

        # 2. Process with AI (use a dedicated "bilibili" session)
        try:
            orchestrator = await self._get_or_create_orchestrator("bilibili")
            result = await orchestrator.process_text(
                text=f"{msg.user_name}说: {msg.text}",
                user_id=str(msg.user_id),
                user_name=msg.user_name,
                channel_id="bilibili",
                source="danmaku",
            )

            # 3. Broadcast response to ALL clients (output_node emits to "bilibili"
            #    session which is not a real socket, so we re-emit as broadcast)
            reply_text = result.get("response_text", "")

            # Broadcast conversation-start
            await self.sio.emit("control", {"signal": "conversation-start"})

            # Broadcast text response via sentence events (original text immediately)
            if reply_text:
                sentence_payload = {
                    "text": reply_text,
                    "seq": 0,
                    "lang": translation_state.source_language.lower()[:2],
                }
                await self.sio.emit("sentence", sentence_payload)
                await self.sio.emit("sentence", {"text": "", "is_complete": True})

                # ── Run translation in background (non-blocking) ──
                if translation_state.enabled:
                    async def _translate_danmaku():
                        try:
                            orchestrator_svc = getattr(orchestrator, "service_context", None)
                            llm = getattr(orchestrator_svc, "llm_engine", None) if orchestrator_svc else None
                            if llm:
                                translate_prompt = (
                                    f"Translate the following text from {translation_state.source_language} "
                                    f"to {translation_state.target_language}. "
                                    f"Output only the translation, no explanations, no quotes.\n\n"
                                    f"Text: {reply_text}\n"
                                    f"Translation:"
                                )
                                translated = await llm.chat(translate_prompt)
                                if translated and translated.strip():
                                    t = translated.strip()
                                    t_lang = translation_state.target_language.lower()[:2]
                                    await self.sio.emit("subtitle.translation", {
                                        "translation": t,
                                        "target_lang": t_lang,
                                    })
                                    logger.info(f"[Bilibili] Translated danmaku reply to {translation_state.target_language}")
                        except Exception as e:
                            logger.warning(f"[Bilibili] Translation failed: {e}")

                    asyncio.create_task(_translate_danmaku())

            # Broadcast emotion
            emotion = result.get("emotion")
            if emotion:
                await self.sio.emit("expression", {"emotion": emotion})

            # Broadcast audio
            tts_audio = result.get("tts_audio")
            if tts_audio:
                await self._broadcast_danmaku_audio(tts_audio)

            # Broadcast conversation-end
            await self.sio.emit("control", {"signal": "conversation-end"})

            # Also emit danmaku.ai_reply for the chat message integration
            if reply_text:
                character_name = "AI"
                persona = orchestrator.service_context.config.get_persona() if orchestrator.service_context else None
                if persona:
                    character_name = persona.name

                await self.sio.emit('danmaku.ai_reply', {
                    'danmaku_text': msg.text,
                    'reply_text': reply_text,
                    'user_name': msg.user_name,
                    'character_name': character_name,
                    'timestamp': time.time(),
                })
        except Exception as e:
            logger.error(f"[Bilibili] Error processing danmaku: {e}")

    async def _broadcast_danmaku_audio(self, tts_audio) -> None:
        """Process TTS audio and broadcast to all clients."""
        import base64
        import os
        from functools import partial

        loop = asyncio.get_running_loop()

        try:
            audio_data = None
            format = "wav"
            volumes = []

            if isinstance(tts_audio, str) and os.path.exists(tts_audio):
                # File path — trim silence, read bytes, compute volumes
                raw_bytes = await loop.run_in_executor(None, partial(_read_file_bytes, tts_audio))
                ext = os.path.splitext(tts_audio)[1].lower()
                format = ext.lstrip('.') if ext else "wav"
                audio_data = base64.b64encode(raw_bytes).decode("utf-8")
                volumes = _compute_volumes(tts_audio) or []

            elif isinstance(tts_audio, bytes):
                # Detect format from magic bytes
                if tts_audio[:4] == b"RIFF":
                    format = "wav"
                elif tts_audio[:3] == b"ID3" or (tts_audio[0] == 0xff and (tts_audio[1] & 0xe0) == 0xe0):
                    format = "mp3"
                elif tts_audio[:4] == b"OggS":
                    format = "ogg"
                audio_data = base64.b64encode(tts_audio).decode("utf-8")
                # Write to temp file for volume computation
                import tempfile
                tmp_audio = tempfile.mktemp(suffix=f".{format}")
                with open(tmp_audio, "wb") as f:
                    f.write(tts_audio)
                volumes = _compute_volumes(tmp_audio) or []

            if audio_data:
                payload = {"audio_data": audio_data, "format": format}
                if volumes:
                    payload["volumes"] = volumes
                await self.sio.emit("audio_with_expression", payload)

        except Exception as e:
            logger.error(f"[Bilibili] Audio broadcasting failed: {e}")

    # ========================================
    # Frontend-initiated Bilibili control
    # ========================================

    async def on_bilibili_connect(self, sid: str, data: dict) -> None:
        """Handle frontend request to connect to a Bilibili live room."""
        room_id = data.get('room_id')
        if not room_id or not isinstance(room_id, int) or room_id <= 0:
            await self.sio.emit('danmaku.status', {
                'connected': False,
                'message': 'Invalid room ID',
            }, to=sid)
            return

        try:
            logger.info(f"[Bilibili] Frontend requested connect to room {room_id}")
            self.start_bilibili(room_id=room_id)
        except Exception as e:
            logger.error(f"[Bilibili] Error connecting to room {room_id}: {e}")
            await self.sio.emit('danmaku.status', {
                'connected': False,
                'message': str(e),
            }, to=sid)

    async def on_bilibili_disconnect(self, sid: str, data: dict) -> None:
        """Handle frontend request to disconnect from Bilibili live room."""
        logger.info("[Bilibili] Frontend requested disconnect")
        self.stop_bilibili()
        await self.sio.emit('danmaku.status', {
            'connected': False,
            'message': 'Disconnected by user',
        })

    async def on_bilibili_update_room(self, sid: str, data: dict) -> None:
        """Handle frontend request to change room ID."""
        room_id = data.get('room_id')
        if not room_id or not isinstance(room_id, int) or room_id <= 0:
            await self.sio.emit('danmaku.status', {
                'connected': False,
                'message': 'Invalid room ID',
            }, to=sid)
            return

        try:
            logger.info(f"[Bilibili] Frontend requested update room to {room_id}")
            self.start_bilibili(room_id=room_id)
            await self.sio.emit('danmaku.status', {
                'connected': True,
                'message': f'Connected to room {room_id}',
            })
        except Exception as e:
            logger.error(f"[Bilibili] Error updating room to {room_id}: {e}")
            await self.sio.emit('danmaku.status', {
                'connected': False,
                'message': str(e),
            }, to=sid)

    def _make_send_callback(self, sid: str):
        async def send_callback(data):
            if isinstance(data, str):
                data = json.loads(data)
            event_type = data.get('type', 'message')
            await self.sio.emit(event_type, data, to=sid)
        return send_callback

    async def _get_or_create_orchestrator(self, sid: str):
        """Get or create LangGraph orchestrator"""
        from anima.config import AppConfig
        from anima.config.live2d import get_live2d_config

        config = self.global_config or AppConfig.load()
        send_callback = self._make_send_callback(sid)

        ctx = await self.session_manager.get_or_create_context(
            sid,
            config,
            send_callback
        )

        live2d_config = get_live2d_config()

        orchestrator = await self.session_manager.get_or_create_orchestrator(
            sid,
            ctx,
            send_callback,
            live2d_config,
            socketio=self.sio,
        )

        await self.session_manager.get_or_create_audio_processor(sid, ctx)

        return orchestrator

    async def broadcast_to_desktop_clients(
        self,
        client_type: str,
        event: str,
        data: dict
    ) -> None:
        """Broadcast message to desktop clients of a specified type"""
        sids = self.desktop_manager.get_clients_by_type(client_type)
        for sid in sids:
            await self.sio.emit(event, data, to=sid)

    # Connection events
    async def on_connect(self, sid: str, environ: dict) -> None:
        """Client connection event"""
        client_type = environ.get("HTTP_USER_AGENT", "")
        is_electron = "electron" in client_type.lower()

        print(f"\n{'='*60}")
        print(f"[OK] Client connected: {sid}")
        print(f"     Type: {'Electron' if is_electron else 'Web'}")
        print(f"{'='*60}\n")
        logger.info(f"Client connected: {sid} (Type: {'Electron' if is_electron else 'Web'})")

        await self.sio.save_session(sid, {
            'connected_at': time.time(),
            'is_electron': is_electron
        })

        await self.sio.emit('connection-established', {
            'message': 'Connection successful',
            'sid': sid,
            'server_time': asyncio.get_event_loop().time()
        }, to=sid)

        if not is_electron:
            await self.sio.emit('control', {
                'type': 'control',
                'text': 'start-mic'
            }, to=sid)
            print(f"[OK] Sent start-mic signal to client {sid}")

    async def on_disconnect(self, sid: str) -> None:
        """Client disconnect event"""
        logger.info(f"Client disconnected: {sid}")
        self.desktop_manager.unregister(sid)
        await self.session_manager.cleanup_session(sid)

    # Conversation events
    async def on_text_input(self, sid: str, data: dict) -> None:
        """Handle text input"""
        text = data.get('text', '')
        logger.info(f"[{sid}] Received text input: {text}")

        if not text:
            return

        try:
            orchestrator = await self._get_or_create_orchestrator(sid)
            await orchestrator.process_text(
                text=text,
                user_id=data.get('user_id', 'user'),
                user_name=data.get('from_name', 'User'),
                channel_id=sid,
            )
        except Exception as e:
            logger.error(f"[{sid}] Error processing text input: {e}")
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e)
            }, to=sid)

    async def on_raw_audio_data(self, sid: str, data: dict) -> None:
        """Handle raw audio data for VAD detection"""
        audio_chunk = data.get('audio', [])

        if not audio_chunk:
            logger.debug(f"[{sid}] Received empty audio data")
            return

        if not hasattr(self, '_raw_audio_first_sids'):
            self._raw_audio_first_sids = set()

        if sid not in self._raw_audio_first_sids:
            self._raw_audio_first_sids.add(sid)
            logger.info(f"[{sid}] [RAW_AUDIO] Starting to receive audio data")

        try:
            await self._get_or_create_orchestrator(sid)

            processor = self.session_manager.get_audio_processor(sid)
            if processor:
                await processor.process_chunk(audio_chunk)
            else:
                logger.error(f"[{sid}] Audio processor not created")

        except Exception as e:
            logger.error(f"[{sid}] VAD processing error: {e}", exc_info=True)

    async def on_mic_audio_end(self, sid: str, data: dict) -> None:
        """Audio input end event"""
        logger.info(f"[{sid}] Audio input ended")

        try:
            processor = self.session_manager.get_audio_processor(sid)
            if processor:
                await processor.process_end()

        except Exception as e:
            logger.error(f"[{sid}] Error processing audio: {e}")
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e)
            }, to=sid)

    async def on_interrupt_signal(self, sid: str, data: dict) -> None:
        """Interrupt signal - stop LLM generation and audio playback"""
        heard_response = data.get('text', '')
        logger.info(f"[{sid}] Received interrupt signal, heard response: {heard_response[:50] if heard_response else '(empty)'}...")

        from anima.orchestration.graph.interrupt_handler import get_interrupt_handler
        interrupt_handler = get_interrupt_handler()
        interrupt_handler.set_interrupt(sid)

        await self.sio.emit('stop_audio', {}, to=sid)

        await self.sio.emit('control', {
            'type': 'control',
            'text': 'interrupted'
        }, to=sid)

    # History events
    async def on_fetch_history_list(self, sid: str, data: dict) -> None:
        """Fetch chat history list"""
        logger.info(f"[{sid}] Requested chat history list")

    async def on_fetch_history(self, sid: str, data: dict) -> None:
        """Fetch specific history record"""
        history_uid = data.get('history_uid')
        logger.info(f"[{sid}] Requested history: {history_uid}")
        messages = []

        await self.sio.emit('history-data', {
            'type': 'history-data',
            'messages': messages
        }, to=sid)

    async def on_clear_history(self, sid: str, data: dict) -> None:
        """Clear conversation history"""
        logger.info(f"[{sid}] Clearing conversation history")

        ctx = self.session_manager.get_context(sid)
        if ctx and ctx.llm_engine:
            ctx.llm_engine.clear_history()
            logger.info(f"[{sid}] Conversation history cleared")

            await self.sio.emit('history-cleared', {
                'type': 'history-cleared'
            }, to=sid)

    async def on_create_new_history(self, sid: str, data: dict) -> None:
        """Create new conversation history"""
        logger.info(f"[{sid}] Creating new conversation history")

        await self.sio.emit('new-history-created', {
            'type': 'new-history-created',
            'history_uid': 'new_history_001'
        }, to=sid)

    # Config events
    async def on_switch_config(self, sid: str, data: dict) -> None:
        """Switch config"""
        config_name = data.get('file', 'default')
        logger.info(f"[{sid}] Switching config: {config_name}")

        try:
            if sid in self.session_manager.orchestrators:
                del self.session_manager.orchestrators[sid]

            await self.sio.emit('config-switched', {
                'type': 'config-switched',
                'message': f'Switched to config: {config_name}'
            }, to=sid)

        except Exception as e:
            logger.error(f"[{sid}] Error switching config: {e}")
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e)
            }, to=sid)

    async def on_set_log_level(self, sid: str, data: dict) -> None:
        """Set backend log level"""
        from anima.utils.logger_manager import logger_manager

        level = data.get('level', 'INFO').upper()
        logger.info(f"[{sid}] Requested to set log level to: {level}")

        success = logger_manager.set_level(level)

        if success and self.user_settings:
            self.user_settings.set_log_level(level)

        await self.sio.emit('log_level_changed', {
            'type': 'log_level_changed',
            'success': success,
            'level': logger_manager.get_level(),
            'message': f'Log level set to {logger_manager.get_level()}' if success else 'Setting failed'
        }, to=sid)

    # Heartbeat
    async def on_get_config(self, sid: str, data: dict) -> None:
        """Return current config (sanitized) to frontend"""
        logger.info(f"[{sid}] Requested config data")
        from anima.config.app import AppConfig
        from anima.config.live2d import Live2DConfig
        import os

        config = self.global_config or AppConfig.load()

        # Read available personas from filesystem
        personas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config', 'personas')
        available_personas = []
        if os.path.isdir(personas_dir):
            available_personas = sorted([
                f.replace('.yaml', '') for f in os.listdir(personas_dir)
                if f.endswith('.yaml')
            ])

        # Read live2d config
        try:
            live2d_cfg = Live2DConfig.load()
            live2d_model_path = live2d_cfg.model.path
        except Exception:
            live2d_model_path = '/live2d/haru/haru_greeter_t03.model3.json'

        # Build safe config (NO api keys, NO secrets)
        config_data = {
            "persona": config.persona,
            "services": {
                "asr": config.services.asr,
                "tts": config.services.tts,
                "agent": config.services.agent,
                "vad": config.services.vad,
            },
            "active_services": {
                "asr": config.asr.type if config.asr else None,
                "tts": config.tts.type if config.tts else None,
                "llm": config.agent.llm_config.type if config.agent and config.agent.llm_config else None,
                "vad": config.vad.type if config.vad else None,
            },
            "system": {
                "host": config.system.host,
                "port": config.system.port,
                "log_level": config.system.log_level,
            },
            "live2d": {
                "model_path": live2d_model_path,
                "enabled": True,
            },
            "available_personas": available_personas,
        }
        await self.sio.emit('config_data', config_data, to=sid)

    async def on_heartbeat(self, sid: str, data: dict) -> None:
        """Heartbeat check"""
        await self.sio.emit('heartbeat-ack', {}, to=sid)

    # Desktop client events
    async def on_desktop_register(self, sid: str, data: dict) -> None:
        """Electron desktop client registration"""
        client_type = data.get('client_type', 'web')

        if not self.desktop_manager.register(sid, client_type):
            await self.sio.emit('error', {
                'type': 'error',
                'message': f'Unknown client type: {client_type}'
            }, to=sid)
            return

        await self.sio.emit('desktop.registered', {
            'client_id': sid,
            'client_type': client_type
        }, to=sid)

    async def on_desktop_live2d_action(self, sid: str, data: dict) -> None:
        """Handle Live2D action request from Electron"""
        action_data = data.get('action', {})
        action_id = data.get('action_id', '')
        queue_policy = data.get('queue_policy', 'append')
        duration = data.get('duration', 0.5)

        result = await self.live2d_manager.enqueue_action(
            action_data=action_data,
            action_id=action_id,
            queue_policy=queue_policy,
            duration=duration
        )

        await self.sio.emit('desktop.action_queued', result, to=sid)

    async def on_desktop_chat_message(self, sid: str, data: dict) -> None:
        """Handle chat message from Electron Chat window"""
        text = data.get('text', '')
        logger.info(f"[Desktop][Chat] Received message: {text[:50]}...")

        try:
            orchestrator = await self._get_or_create_orchestrator(sid)
            await orchestrator.process_text(
                text=text,
                user_id='user',
                user_name='User',
                channel_id=sid,
            )

        except Exception as e:
            logger.error(f"[{sid}] Error processing desktop chat message: {e}")
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e)
            }, to=sid)

    async def on_desktop_voice_start(self, sid: str, data: dict) -> None:
        """Start voice input"""
        logger.info(f"[Desktop][Chat] Voice input started")
        await self.sio.emit('desktop.voice_started', {}, to=sid)

    async def on_desktop_voice_stop(self, sid: str, data: dict) -> None:
        """Stop voice input"""
        logger.info(f"[Desktop][Chat] Voice input stopped")
        await self.sio.emit('desktop.voice_stopped', {}, to=sid)

    # Memory organization events
    async def on_memory_organize(self, sid: str, data: dict) -> None:
        """Trigger memory organization"""
        logger.info(f"[{sid}] Received memory organization request")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system:
                await self.sio.emit('memory.organize.result', {
                    'type': 'error',
                    'message': 'Memory system not initialized'
                }, to=sid)
                return

            memory_system = ctx.memory_system
            if not memory_system._wiki_manager:
                await self.sio.emit('memory.organize.result', {
                    'type': 'error',
                    'message': 'Wiki manager not initialized'
                }, to=sid)
                return

            from anima.memory.wiki.organizer import WikiOrganizer

            # Get LLM client from service context
            llm_client = None
            if ctx.llm_engine:
                # Use the LLMInterface directly (has async chat method)
                llm_client = ctx.llm_engine

            organizer = WikiOrganizer(
                wiki=memory_system._wiki_manager,
                llm_client=llm_client,
            )

            async def progress_callback(text, pct):
                await self.sio.emit('memory.organize.progress', {
                    'text': text,
                    'progress': pct,
                }, to=sid)

            result = await organizer.organize(progress_callback=progress_callback)

            await self.sio.emit('memory.organize.result', {
                'type': 'success',
                'merges': result.get('merges', 0),
                'synthesis': result.get('synthesis', 0),
                'updates': result.get('updates', 0),
                'errors': result.get('errors', []),
            }, to=sid)

            logger.info(
                f"[{sid}] Memory organization complete: "
                f"merges={result.get('merges', 0)}, "
                f"synthesis={result.get('synthesis', 0)}, "
                f"updates={result.get('updates', 0)}"
            )

        except Exception as e:
            logger.error(f"[{sid}] Memory organization failed: {e}", exc_info=True)
            await self.sio.emit('memory.organize.result', {
                'type': 'error',
                'message': str(e),
            }, to=sid)


    async def on_translation_configure(self, sid: str, data: dict) -> None:
        """Update translation configuration at runtime."""
        target_language = data.get("target_language")
        if target_language:
            translation_state.target_language = target_language
            logger.info(f"[{sid}] Translation target language updated to: {target_language}")
            await self.sio.emit("translation.status", {
                "target_language": translation_state.target_language,
                "enabled": translation_state.enabled,
            }, to=sid)
        else:
            await self.sio.emit("translation.status", {
                "target_language": translation_state.target_language,
                "enabled": translation_state.enabled,
            }, to=sid)

    # ========================================
    # Memory: Wiki Pages
    # ========================================

    async def on_get_wiki_pages(self, sid: str, data: dict) -> dict:
        """获取 wiki 页面列表"""
        try:
            # Try session-level memory_system
            ctx = self.session_manager.get_context(sid)
            if ctx and ctx.memory_system and hasattr(ctx.memory_system, '_wiki_manager'):
                wiki = ctx.memory_system._wiki_manager
                pages = []
                for rel in wiki.list_pages():
                    page = wiki.read_page(rel)
                    if page:
                        pages.append({
                            'path': page.path,
                            'title': page.title,
                            'page_type': page.page_type.value,
                            'content': page.content[:200],
                            'tags': page.tags,
                            'updated_at': page.updated_at.isoformat() if page.updated_at else '',
                        })
                logger.info(f"[{sid}] Wiki pages (from memory): {len(pages)}")
                return {'pages': pages}

            # Fallback: read wiki files directly from workspace
            from pathlib import Path
            import yaml
            workspace = Path('./memory_db')
            wiki_dir = workspace / 'wiki'
            if not wiki_dir.exists():
                return {'pages': []}

            pages = []
            # Map plural directory names to singular (frontend filter expects singular)
            TYPE_MAP = {"entities": "entity", "concepts": "concept",
                        "sources": "source", "synthesis": "synthesis", "memes": "meme"}
            for md_file in sorted(wiki_dir.rglob('*.md')):
                rel = str(md_file.relative_to(wiki_dir)).replace("\\", "/")
                content = md_file.read_text(encoding='utf-8')[:500]
                title = md_file.stem
                parent = md_file.parent.name if md_file.parent != wiki_dir else 'source'
                pages.append({
                    'path': rel,
                    'title': title,
                    'page_type': TYPE_MAP.get(parent, parent),
                    'content': content,
                    'tags': [],
                    'updated_at': str(Path(md_file).stat().st_mtime),
                })
            logger.info(f"[{sid}] Wiki pages (from disk): {len(pages)} pages, types={list(set(p['page_type'] for p in pages))}")
            return {'pages': pages}
        except Exception as e:
            logger.error(f"[{sid}] get_wiki_pages failed: {e}")
            return {'pages': []}

    # ========================================
    # Persona Runtime Switching
    # ========================================

    async def on_set_persona(self, sid: str, data: dict) -> None:
        """运行时切换人设"""
        persona_name = data.get('persona_name', '')
        if not persona_name:
            logger.warning(f"[{sid}] 切换人设失败: 人设名称为空")
            await self.sio.emit('error', {
                'type': 'error',
                'message': 'persona_name is required'
            }, to=sid)
            return

        logger.info(f"[{sid}] 切换人设: {persona_name}")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx:
                await self.sio.emit('error', {
                    'type': 'error',
                    'message': '会话未初始化'
                }, to=sid)
                return

            from anima.config.persona import PersonaConfig

            # Load new persona
            new_persona = PersonaConfig.load(persona_name)
            if not new_persona:
                await self.sio.emit('error', {
                    'type': 'error',
                    'message': f'无法加载人设: {persona_name}'
                }, to=sid)
                return

            # Update global config persona cache
            if self.global_config:
                self.global_config.persona = persona_name
                self.global_config._persona = None  # Invalidate cache

            # Rebuild system prompt and push to LLM engine
            if ctx.llm_engine and ctx.config:
                live2d_prompt = None
                try:
                    from anima.config.live2d import get_live2d_config
                    from anima.avatar.prompts import EmotionPromptBuilder
                    live2d_cfg = get_live2d_config()
                    if live2d_cfg and live2d_cfg.enabled:
                        builder = EmotionPromptBuilder.from_config(
                            {"valid_emotions": live2d_cfg.valid_emotions}
                        )
                        live2d_prompt = builder.build_prompt()
                except Exception:
                    pass

                new_system_prompt = ctx.config.get_system_prompt(live2d_prompt=live2d_prompt)
                ctx.llm_engine.set_system_prompt(new_system_prompt)
                logger.info(f"[{sid}] 已更新 LLM 系统提示词")

            # Notify orchestrator to refresh system prompt on next run
            orchestrator = self.session_manager.get_orchestrator(sid)
            if orchestrator:
                logger.info(f"[{sid}] 编排器已感知人设变更")

            logger.info(f"[{sid}] 人设切换完成: {persona_name}")
            await self.sio.emit('persona_updated', {
                'persona_name': persona_name,
            }, to=sid)

        except Exception as e:
            logger.error(f"[{sid}] 切换人设失败: {e}", exc_info=True)
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e),
            }, to=sid)

    # ========================================
    # Memory Evolution: MemePool CRUD
    # ========================================

    async def on_meme_add(self, sid: str, data: dict) -> None:
        """添加梗到 MemePool"""
        text = data.get('text', '')
        context_hint = data.get('context_hint', '')
        tags = data.get('tags', [])
        logger.info(f"[{sid}] 添加梗: {text[:50]}...")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, 'meme_pool') or not ctx.memory_system.meme_pool:
                await self.sio.emit('error', {
                    'type': 'error',
                    'message': 'MemePool 未初始化'
                }, to=sid)
                return

            from anima.memory.meme import MemeSource
            meme = ctx.memory_system.meme_pool.add_meme(
                text=text,
                context_hint=context_hint,
                source=MemeSource.USER,
                tags=tags,
            )

            await self.sio.emit('meme_added', {
                'meme': meme.to_dict(),
            }, to=sid)

            logger.info(f"[{sid}] 梗已添加: {meme.id}")

        except Exception as e:
            logger.error(f"[{sid}] 添加梗失败: {e}", exc_info=True)
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e),
            }, to=sid)

    async def on_meme_rate(self, sid: str, data: dict) -> None:
        """评分梗"""
        meme_id = data.get('meme_id', '')
        score = data.get('score', 0.0)
        logger.info(f"[{sid}] 评分梗: {meme_id} = {score}")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, 'meme_pool') or not ctx.memory_system.meme_pool:
                await self.sio.emit('error', {
                    'type': 'error',
                    'message': 'MemePool 未初始化'
                }, to=sid)
                return

            meme_pool = ctx.memory_system.meme_pool

            # Score after use with effectiveness = score
            meme_pool.score_after_use(meme_id, effectiveness=score)

            await self.sio.emit('meme_updated', {
                'meme_id': meme_id,
                'score': score,
            }, to=sid)

            logger.info(f"[{sid}] 梗评分完成: {meme_id}")

        except Exception as e:
            logger.error(f"[{sid}] 评分梗失败: {e}", exc_info=True)
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e),
            }, to=sid)

    async def on_meme_delete(self, sid: str, data: dict) -> None:
        """删除梗（标记为非活跃）"""
        meme_id = data.get('meme_id', '')
        logger.info(f"[{sid}] 删除梗: {meme_id}")

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, 'meme_pool') or not ctx.memory_system.meme_pool:
                await self.sio.emit('error', {
                    'type': 'error',
                    'message': 'MemePool 未初始化'
                }, to=sid)
                return

            meme_pool = ctx.memory_system.meme_pool
            meme_pool.store.set_active(meme_id, active=False)

            await self.sio.emit('meme_updated', {
                'meme_id': meme_id,
                'active': False,
            }, to=sid)

            logger.info(f"[{sid}] 梗已删除: {meme_id}")

        except Exception as e:
            logger.error(f"[{sid}] 删除梗失败: {e}", exc_info=True)
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e),
            }, to=sid)

    # ── Meme Review (筛选器) ──────────────────────────────────────────

    async def on_meme_list(self, sid: str, data: dict) -> None:
        """获取待筛选梗列表（meme:list）"""
        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, 'meme_pool'):
                await self.sio.emit('meme:list', {'memes': [], 'error': 'MemePool 未初始化'}, to=sid)
                return

            meme_pool = ctx.memory_system.meme_pool
            source_platform = data.get('source_platform', '')
            limit = data.get('limit', 50)

            active = meme_pool.store.list_active()
            pending = [m for m in active if m.review_status == 'pending']
            if source_platform:
                pending = [m for m in pending if m.source_platform == source_platform]
            pending = pending[:limit]

            memes_data = []
            for m in pending:
                item = {
                    'id': m.id, 'text': m.text, 'context_hint': m.context_hint,
                    'tags': m.tags, 'source_platform': m.source_platform,
                    'base_score': m.base_score,
                }
                if m.cognitive_analysis:
                    item['cognitive_analysis'] = {
                        'humor_mechanism': m.cognitive_analysis.humor_mechanism,
                        'emotional_tone': m.cognitive_analysis.emotional_tone,
                        'persona_fit_score': m.cognitive_analysis.persona_fit_score,
                        'source_url': m.cognitive_analysis.source_url,
                    }
                memes_data.append(item)

            await self.sio.emit('meme:list', {'memes': memes_data, 'total': len(memes_data)}, to=sid)
            logger.info(f"[{sid}] meme:list → {len(memes_data)} pending")

        except Exception as e:
            logger.error(f"[{sid}] meme:list error: {e}", exc_info=True)
            await self.sio.emit('meme:list', {'memes': [], 'error': str(e)}, to=sid)

    async def on_meme_review(self, sid: str, data: dict) -> None:
        """提交梗筛选结果（meme:review）"""
        import random
        meme_id = data.get('meme_id', '')
        status = data.get('status', '')

        if not meme_id or status not in ('good', 'bad'):
            await self.sio.emit('meme:review', {'ok': False, 'error': '无效参数'}, to=sid)
            return

        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, 'meme_pool'):
                await self.sio.emit('meme:review', {'ok': False, 'error': 'MemePool 未初始化'}, to=sid)
                return

            meme_pool = ctx.memory_system.meme_pool
            meme = None
            for m in meme_pool.store.list_active():
                if m.id == meme_id:
                    meme = m
                    break
            if not meme:
                for m in meme_pool.store.list_discarded():
                    if m.id == meme_id:
                        meme = m
                        break

            if not meme:
                await self.sio.emit('meme:review', {'ok': False, 'error': f'梗未找到: {meme_id}'}, to=sid)
                return

            meme.review_status = status
            if status == 'good':
                meme.base_score = min(1.0, meme.base_score + 0.2)
                meme.current_score = meme.base_score
            else:
                meme.is_active = False

            # AI反馈（尝试LLM，失败则降级）
            feedback = await self._generate_meme_feedback(meme.text, meme.tags, status, ctx)
            if feedback and meme.cognitive_analysis:
                meme.cognitive_analysis.roast = feedback
            elif feedback:
                from anima.memory.meme.models import CognitiveAnalysis
                meme.cognitive_analysis = CognitiveAnalysis(roast=feedback)

            meme_pool.store.update(meme)
            await self.sio.emit('meme:review', {
                'ok': True, 'meme_id': meme_id, 'status': status, 'feedback': feedback,
            }, to=sid)
            logger.info(f"[{sid}] meme:review {meme_id} → {status}")

        except Exception as e:
            logger.error(f"[{sid}] meme:review error: {e}", exc_info=True)
            await self.sio.emit('meme:review', {'ok': False, 'error': str(e)}, to=sid)

    async def on_meme_dataset(self, sid: str, data: dict) -> None:
        """导出已筛选的高质量梗数据集（meme:dataset）"""
        try:
            ctx = self.session_manager.get_context(sid)
            if not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, 'meme_pool'):
                await self.sio.emit('meme:dataset', {'memes': [], 'error': 'MemePool 未初始化'}, to=sid)
                return

            meme_pool = ctx.memory_system.meme_pool
            source_platform = data.get('source_platform', '')
            all_active = meme_pool.store.list_active()
            inactive = meme_pool.store.list_discarded()
            good = [m for m in all_active + inactive if m.review_status == 'good']
            if source_platform:
                good = [m for m in good if m.source_platform == source_platform]

            dataset = []
            for m in good:
                item = {'text': m.text, 'context_hint': m.context_hint, 'tags': m.tags, 'source_platform': m.source_platform}
                if m.cognitive_analysis:
                    item.update({
                        'humor_mechanism': m.cognitive_analysis.humor_mechanism,
                        'emotional_tone': m.cognitive_analysis.emotional_tone,
                        'usage_example': m.cognitive_analysis.usage_example,
                        'source_url': m.cognitive_analysis.source_url,
                    })
                dataset.append(item)

            await self.sio.emit('meme:dataset', {'memes': dataset, 'total': len(dataset)}, to=sid)
            logger.info(f"[{sid}] meme:dataset → {len(dataset)} good memes")

        except Exception as e:
            logger.error(f"[{sid}] meme:dataset error: {e}", exc_info=True)
            await self.sio.emit('meme:dataset', {'memes': [], 'error': str(e)}, to=sid)

    async def _generate_meme_feedback(self, text: str, tags: list, status: str, ctx) -> str:
        """生成AI反馈（赞赏或吐槽），LLM不可用时降级到模板"""
        import random
        GOOD_TPL = [
            "这个梗的幽默结构完整，可以收入数据库。",
            "双关/反讽/荒诞机制运作正常——通过。",
            "数据支持：此梗具备传播潜力。",
            "逻辑链完整，笑点部署合理——合格。",
            "这个观察角度不错，值得保留。",
        ]
        BAD_TPL = [
            "这个梗的幽默密度≈真空，建议回炉重造。",
            "数据表明：此梗笑点缺失，情感共鸣为零。",
            "算法分析结果：该梗需要更多人类智慧注入。",
            "统计显示，此梗的传播系数接近于零——它不配。",
            "冷到连我的散热系统都不用工作了。",
        ]
        # Try LLM if available via service context
        try:
            llm = getattr(ctx, 'llm_engine', None) or getattr(ctx, 'llm', None)
            if llm and hasattr(llm, 'chat'):
                prompt = (
                    f"梗: {text}\n标签: {', '.join(tags) if tags else '无'}\n"
                    f"用户评价: {'好梗' if status == 'good' else '烂梗'}\n"
                    f"{'请用15-30字赞赏这个梗的优点。' if status == 'good' else '请用20-40字吐槽这个梗的问题。'}"
                    f"语气：理性冷幽默AI视角，禁止语气词。只返回点评文本。"
                )
                result = await llm.chat(messages=[{"role": "user", "content": prompt}])
                content = result.get("content", "") if isinstance(result, dict) else str(result)
                content = content.strip().strip('"').strip("'")
                if content:
                    return content[:100]
        except Exception as e:
            logger.debug(f"[MemeReview] LLM feedback failed: {e}")

        return random.choice(GOOD_TPL if status == 'good' else BAD_TPL)

    async def on_set_personality_mode(self, sid: str, data: dict) -> None:
        """设置个性模式（运行时切换）"""
        mode = data.get('mode', '')
        if not mode:
            logger.warning(f"[{sid}] 设置个性模式失败: mode 为空")
            await self.sio.emit('error', {
                'type': 'error',
                'message': 'mode is required'
            }, to=sid)
            return

        logger.info(f"[{sid}] 设置个性模式: {mode}")

        try:
            orchestrator = self.session_manager.get_orchestrator(sid)

            # Store mode on orchestrator for runtime access by nodes
            if orchestrator:
                if not hasattr(orchestrator, '_personality_mode'):
                    orchestrator._personality_mode = {}
                orchestrator._personality_mode['mode'] = mode
                logger.info(f"[{sid}] 编排器已更新个性模式")

            await self.sio.emit('personality_updated', {
                'mode': mode,
            }, to=sid)

            logger.info(f"[{sid}] 个性模式已设置: {mode}")

        except Exception as e:
            logger.error(f"[{sid}] 设置个性模式失败: {e}", exc_info=True)
            await self.sio.emit('error', {
                'type': 'error',
                'message': str(e),
            }, to=sid)


def register_routes(
    sio: "AsyncServer",
    session_manager: "SessionManager",
    desktop_manager: Optional[DesktopClientManager] = None,
    live2d_manager: Optional[Live2DManager] = None,
    bilibili_config: Optional[Dict[str, Any]] = None,
) -> RouteHandlers:
    """Register all routes to the Socket.IO server"""
    handlers = RouteHandlers(
        sio,
        session_manager,
        desktop_manager,
        live2d_manager
    )

    # Start Bilibili danmaku service if configured
    if bilibili_config and bilibili_config.get("enabled", False):
        room_id = bilibili_config.get("room_id")
        if room_id:
            handlers.start_bilibili(
                room_id=int(room_id),
                sessdata=bilibili_config.get("sessdata", ""),
            )

    # Connection events
    sio.on('connect', handlers.on_connect)
    sio.on('disconnect', handlers.on_disconnect)

    # Conversation events
    sio.on('text_input', handlers.on_text_input)
    sio.on('raw_audio_data', handlers.on_raw_audio_data)
    sio.on('mic_audio_end', handlers.on_mic_audio_end)
    sio.on('interrupt_signal', handlers.on_interrupt_signal)

    # History events
    sio.on('fetch_history_list', handlers.on_fetch_history_list)
    sio.on('fetch_history', handlers.on_fetch_history)
    sio.on('clear_history', handlers.on_clear_history)
    sio.on('create_new_history', handlers.on_create_new_history)

    # Config events
    sio.on('switch_config', handlers.on_switch_config)
    sio.on('set_log_level', handlers.on_set_log_level)

    # Config events (read)
    sio.on('get_config', handlers.on_get_config)

    # Heartbeat
    sio.on('heartbeat', handlers.on_heartbeat)

    # Desktop client events
    sio.on('desktop_register', handlers.on_desktop_register)
    sio.on('desktop_live2d_action', handlers.on_desktop_live2d_action)
    sio.on('desktop_chat_message', handlers.on_desktop_chat_message)
    sio.on('desktop_voice_start', handlers.on_desktop_voice_start)
    sio.on('desktop_voice_stop', handlers.on_desktop_voice_stop)

    # Bilibili frontend control events
    sio.on('bilibili.connect', handlers.on_bilibili_connect)
    sio.on('bilibili.disconnect', handlers.on_bilibili_disconnect)
    sio.on('bilibili.update_room', handlers.on_bilibili_update_room)

    # Memory organization events
    sio.on('memory_organize', handlers.on_memory_organize)

    # Translation configuration events
    sio.on('translation.configure', handlers.on_translation_configure)

    # Memory: Wiki Pages
    sio.on('get_wiki_pages', handlers.on_get_wiki_pages)

    # Persona runtime switching
    sio.on('set_persona', handlers.on_set_persona)

    # Memory Evolution: MemePool CRUD
    sio.on('meme_add', handlers.on_meme_add)
    sio.on('meme_rate', handlers.on_meme_rate)
    sio.on('meme_delete', handlers.on_meme_delete)

    # Meme Review (筛选器)
    sio.on('meme:list', handlers.on_meme_list)
    sio.on('meme:review', handlers.on_meme_review)
    sio.on('meme:dataset', handlers.on_meme_dataset)

    # Personality mode runtime switching
    sio.on('set_personality_mode', handlers.on_set_personality_mode)

    logger.info("WebSocket routes registered")
    return handlers
