"""WebSocket route definitions — thin delegation layer.

All handler logic is extracted into server/handlers/ modules.
RouteHandlers acts as a facade that delegates to domain-specific handlers.
"""

import json
import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING

from loguru import logger

from .desktop import DesktopClientManager
from .live2d import Live2DManager
from .handlers.admin_handlers import AdminHandlers
from .handlers.bilibili_handlers import BilibiliHandlers
from .handlers.chat_handlers import ChatHandlers
from .handlers.live2d_handlers import Live2DHandlers

if TYPE_CHECKING:
    from .session import SessionManager
    from socketio import AsyncServer


class RouteHandlers:
    """Facade that delegates Socket.IO events to domain-specific handlers.

    Maintains the same external interface for backward compatibility.
    All handler logic lives in server/handlers/.
    """

    def __init__(
        self,
        sio: "AsyncServer",
        session_manager: "SessionManager",
        desktop_manager: Optional[DesktopClientManager] = None,
        live2d_manager: Optional[Live2DManager] = None,
    ):
        # Infrastructure
        self.sio = sio
        self.session_manager = session_manager
        self.desktop_manager = desktop_manager or DesktopClientManager()
        self.live2d_manager = live2d_manager or Live2DManager()

        # Domain handlers — Admin first (shared dependency), then others
        self.admin = AdminHandlers(
            sio, session_manager, self.desktop_manager, self.live2d_manager
        )
        self.bilibili = BilibiliHandlers(sio, session_manager, self.admin)
        self.chat = ChatHandlers(sio, session_manager, self.admin)
        self.live2d = Live2DHandlers(sio, self.live2d_manager, self.admin)

        # Backward-compat: set global_config/user_settings on admin
        self.global_config = self.admin.global_config
        self.user_settings = self.admin.user_settings

        # Wire up Live2D callback
        self.live2d._setup_live2d_callback()

    # ── Config setters (backward compat) ──────────────────────────────

    # ── Backward-compat properties for internal state moved to handlers ─

    @property
    def _bilibili_service(self):
        """Backward-compat: Bilibili danmaku service (now on BilibiliHandlers)."""
        return self.bilibili._bilibili_service

    @_bilibili_service.setter
    def _bilibili_service(self, value):
        self.bilibili._bilibili_service = value

    @property
    def _main_loop(self):
        """Backward-compat: main event loop (now on BilibiliHandlers)."""
        return self.bilibili._main_loop

    @_main_loop.setter
    def _main_loop(self, value):
        self.bilibili._main_loop = value

    # ── Config setters (backward compat) ──────────────────────────────

    def set_global_config(self, config) -> None:
        """Set global config — delegates to AdminHandlers."""
        self.admin.set_global_config(config)
        self.global_config = self.admin.global_config

    def set_user_settings(self, user_settings) -> None:
        """Set user settings — delegates to AdminHandlers."""
        self.admin.set_user_settings(user_settings)
        self.user_settings = self.admin.user_settings

    # ── Shared utility (backward compat) ─────────────────────────────

    async def broadcast_to_desktop_clients(
        self, client_type: str, event: str, data: dict
    ) -> None:
        """Broadcast to desktop clients — delegates to AdminHandlers."""
        return await self.admin.broadcast_to_desktop_clients(
            client_type, event, data
        )

    # ── Bilibili service (backward compat — called by WebSocketServer) ─

    def start_bilibili(self, room_id: int, sessdata: str = "") -> None:
        """Start Bilibili danmaku service — delegates to BilibiliHandlers."""
        return self.bilibili.start_bilibili(room_id, sessdata)

    def stop_bilibili(self) -> None:
        """Stop Bilibili danmaku service — delegates to BilibiliHandlers."""
        return self.bilibili.stop_bilibili()

    # ── Connection events ─────────────────────────────────────────────

    async def on_connect(self, sid: str, environ: dict) -> None:
        return await self.admin.on_connect(sid, environ)

    async def on_disconnect(self, sid: str) -> None:
        return await self.admin.on_disconnect(sid)

    # ── Conversation events ───────────────────────────────────────────

    async def on_text_input(self, sid: str, data: dict) -> None:
        return await self.chat.on_text_input(sid, data)

    async def on_raw_audio_data(self, sid: str, data: dict) -> None:
        return await self.chat.on_raw_audio_data(sid, data)

    async def on_mic_audio_end(self, sid: str, data: dict) -> None:
        return await self.chat.on_mic_audio_end(sid, data)

    async def on_interrupt_signal(self, sid: str, data: dict) -> None:
        return await self.chat.on_interrupt_signal(sid, data)

    # ── History events ────────────────────────────────────────────────

    async def on_fetch_history_list(self, sid: str, data: dict) -> None:
        return await self.chat.on_fetch_history_list(sid, data)

    async def on_fetch_history(self, sid: str, data: dict) -> None:
        return await self.chat.on_fetch_history(sid, data)

    async def on_clear_history(self, sid: str, data: dict) -> None:
        return await self.chat.on_clear_history(sid, data)

    async def on_create_new_history(self, sid: str, data: dict) -> None:
        return await self.chat.on_create_new_history(sid, data)

    # ── Config events ─────────────────────────────────────────────────

    async def on_switch_config(self, sid: str, data: dict) -> None:
        return await self.admin.on_switch_config(sid, data)

    async def on_set_log_level(self, sid: str, data: dict) -> None:
        return await self.admin.on_set_log_level(sid, data)

    async def on_get_config(self, sid: str, data: dict) -> None:
        return await self.admin.on_get_config(sid, data)

    # ── Heartbeat ─────────────────────────────────────────────────────

    async def on_heartbeat(self, sid: str, data: dict) -> None:
        return await self.admin.on_heartbeat(sid, data)

    # ── Desktop client events ─────────────────────────────────────────

    async def on_desktop_register(self, sid: str, data: dict) -> None:
        return await self.live2d.on_desktop_register(sid, data)

    async def on_desktop_live2d_action(self, sid: str, data: dict) -> None:
        return await self.live2d.on_desktop_live2d_action(sid, data)

    async def on_desktop_chat_message(self, sid: str, data: dict) -> None:
        return await self.live2d.on_desktop_chat_message(sid, data)

    async def on_desktop_voice_start(self, sid: str, data: dict) -> None:
        return await self.live2d.on_desktop_voice_start(sid, data)

    async def on_desktop_voice_stop(self, sid: str, data: dict) -> None:
        return await self.live2d.on_desktop_voice_stop(sid, data)

    # ── Bilibili frontend control events ──────────────────────────────

    async def on_bilibili_connect(self, sid: str, data: dict) -> None:
        return await self.bilibili.on_bilibili_connect(sid, data)

    async def on_bilibili_disconnect(self, sid: str, data: dict) -> None:
        return await self.bilibili.on_bilibili_disconnect(sid, data)

    async def on_bilibili_update_room(self, sid: str, data: dict) -> None:
        return await self.bilibili.on_bilibili_update_room(sid, data)

    # ── Memory / Wiki / Meme / Persona events ─────────────────────────

    async def on_memory_organize(self, sid: str, data: dict) -> None:
        return await self.admin.on_memory_organize(sid, data)

    async def on_translation_configure(self, sid: str, data: dict) -> None:
        return await self.admin.on_translation_configure(sid, data)

    async def on_get_wiki_pages(self, sid: str, data: dict) -> dict:
        return await self.admin.on_get_wiki_pages(sid, data)

    async def on_set_persona(self, sid: str, data: dict) -> None:
        return await self.admin.on_set_persona(sid, data)

    async def on_set_personality_mode(self, sid: str, data: dict) -> None:
        return await self.admin.on_set_personality_mode(sid, data)

    async def on_meme_add(self, sid: str, data: dict) -> None:
        return await self.admin.on_meme_add(sid, data)

    async def on_meme_rate(self, sid: str, data: dict) -> None:
        return await self.admin.on_meme_rate(sid, data)

    async def on_meme_delete(self, sid: str, data: dict) -> None:
        return await self.admin.on_meme_delete(sid, data)

    async def on_meme_list(self, sid: str, data: dict) -> None:
        return await self.admin.on_meme_list(sid, data)

    async def on_meme_review(self, sid: str, data: dict) -> None:
        return await self.admin.on_meme_review(sid, data)

    async def on_meme_dataset(self, sid: str, data: dict) -> None:
        return await self.admin.on_meme_dataset(sid, data)

    async def on_meme_collect(self, sid: str, data: dict) -> None:
        return await self.admin.on_meme_collect(sid, data)


def register_routes(
    sio: "AsyncServer",
    session_manager: "SessionManager",
    desktop_manager: Optional[DesktopClientManager] = None,
    live2d_manager: Optional[Live2DManager] = None,
    bilibili_config: Optional[Dict[str, Any]] = None,
) -> RouteHandlers:
    """Register all routes to the Socket.IO server."""
    handlers = RouteHandlers(
        sio, session_manager, desktop_manager, live2d_manager
    )

    # Start Bilibili danmaku service if configured
    if bilibili_config and bilibili_config.get("enabled", False):
        room_id = bilibili_config.get("room_id")
        if room_id:
            handlers.bilibili.start_bilibili(
                room_id=int(room_id),
                sessdata=bilibili_config.get("sessdata", ""),
            )

    # Connection events
    sio.on("connect", handlers.on_connect)
    sio.on("disconnect", handlers.on_disconnect)

    # Conversation events
    sio.on("text_input", handlers.on_text_input)
    sio.on("raw_audio_data", handlers.on_raw_audio_data)
    sio.on("mic_audio_end", handlers.on_mic_audio_end)
    sio.on("interrupt_signal", handlers.on_interrupt_signal)

    # History events
    sio.on("fetch_history_list", handlers.on_fetch_history_list)
    sio.on("fetch_history", handlers.on_fetch_history)
    sio.on("clear_history", handlers.on_clear_history)
    sio.on("create_new_history", handlers.on_create_new_history)

    # Config events
    sio.on("switch_config", handlers.on_switch_config)
    sio.on("set_log_level", handlers.on_set_log_level)
    sio.on("get_config", handlers.on_get_config)

    # Heartbeat
    sio.on("heartbeat", handlers.on_heartbeat)

    # Desktop client events
    sio.on("desktop_register", handlers.on_desktop_register)
    sio.on("desktop_live2d_action", handlers.on_desktop_live2d_action)
    sio.on("desktop_chat_message", handlers.on_desktop_chat_message)
    sio.on("desktop_voice_start", handlers.on_desktop_voice_start)
    sio.on("desktop_voice_stop", handlers.on_desktop_voice_stop)

    # Bilibili frontend control events
    sio.on("bilibili.connect", handlers.on_bilibili_connect)
    sio.on("bilibili.disconnect", handlers.on_bilibili_disconnect)
    sio.on("bilibili.update_room", handlers.on_bilibili_update_room)

    # Memory organization events
    sio.on("memory_organize", handlers.on_memory_organize)

    # Translation configuration events
    sio.on("translation.configure", handlers.on_translation_configure)

    # Memory: Wiki Pages
    sio.on("get_wiki_pages", handlers.on_get_wiki_pages)

    # Persona runtime switching
    sio.on("set_persona", handlers.on_set_persona)

    # Memory Evolution: MemePool CRUD
    sio.on("meme_add", handlers.on_meme_add)
    sio.on("meme_rate", handlers.on_meme_rate)
    sio.on("meme_delete", handlers.on_meme_delete)

    # Meme Review (筛选器)
    sio.on("meme:list", handlers.on_meme_list)
    sio.on("meme:review", handlers.on_meme_review)
    sio.on("meme:dataset", handlers.on_meme_dataset)
    sio.on("meme:collect", handlers.on_meme_collect)

    # Personality mode runtime switching
    sio.on("set_personality_mode", handlers.on_set_personality_mode)

    logger.info("WebSocket routes registered")
    return handlers
