"""WebSocket route definitions - handle conversations using the LangGraph orchestrator"""

import json
import time
import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING
from loguru import logger

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
        live2d_manager: Optional[Live2DManager] = None
    ):
        self.sio = sio
        self.session_manager = session_manager
        self.desktop_manager = desktop_manager or DesktopClientManager()
        self.live2d_manager = live2d_manager or Live2DManager()

        self.global_config = None
        self.user_settings = None
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


def register_routes(
    sio: "AsyncServer",
    session_manager: "SessionManager",
    desktop_manager: Optional[DesktopClientManager] = None,
    live2d_manager: Optional[Live2DManager] = None
) -> RouteHandlers:
    """Register all routes to the Socket.IO server"""
    handlers = RouteHandlers(
        sio,
        session_manager,
        desktop_manager,
        live2d_manager
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

    # Memory organization events
    sio.on('memory_organize', handlers.on_memory_organize)

    logger.info("WebSocket routes registered")
    return handlers
