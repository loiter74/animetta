"""
Configuration event handlers — config switching, log level, heartbeat, translation.
"""

import asyncio
import os
from typing import TYPE_CHECKING

from loguru import logger

from animetta import $$$
from .base_handler import BaseSocketHandler

if TYPE_CHECKING:
    from socketio import AsyncServer
    from ..session import SessionManager
    from ..desktop import DesktopClientManager
    from ..live2d import Live2DManager


class ConfigHandlers(BaseSocketHandler):
    """Configuration and utility event handlers.

    Inherits shared infrastructure from BaseSocketHandler.
    """

    def __init__(
        self,
        sio: "AsyncServer",
        session_manager: "SessionManager",
        desktop_manager: "DesktopClientManager",
        live2d_manager: "Live2DManager",
    ):
        super().__init__(sio, session_manager, desktop_manager, live2d_manager)

    # ── Config events ─────────────────────────────────────────────────

    async def on_switch_config(self, sid: str, data: dict) -> None:
        """Switch config."""
        config_name = data.get("file", "default")
        logger.info(f"[{sid}] Switching config: {config_name}")

        try:
            if sid in self.session_manager.orchestrators:
                del self.session_manager.orchestrators[sid]

            await self.sio.emit(
                "config-switched",
                {
                    "type": "config-switched",
                    "message": f"Switched to config: {config_name}",
                },
                to=sid,
            )

        except Exception as e:
            logger.error(f"[{sid}] Error switching config: {e}")
            await self.sio.emit("error", {"type": "error", "message": str(e)}, to=sid)

    async def on_set_log_level(self, sid: str, data: dict) -> None:
        """Set backend log level."""
        from animetta import $$$

        level = data.get("level", "INFO").upper()
        logger.info(f"[{sid}] Requested to set log level to: {level}")

        success = logger_manager.set_level(level)

        if success and self.user_settings:
            self.user_settings.set_log_level(level)

        await self.sio.emit(
            "log_level_changed",
            {
                "type": "log_level_changed",
                "success": success,
                "level": logger_manager.get_level(),
                "message": f"Log level set to {logger_manager.get_level()}"
                if success
                else "Setting failed",
            },
            to=sid,
        )

    async def on_get_config(self, sid: str, data: dict) -> None:
        """Return current config (sanitized) to frontend."""
        logger.info(f"[{sid}] Requested config data")
        from animetta import $$$
        from animetta import $$$

        config = self.global_config or AppConfig.load()

        # Read available personas from filesystem
        personas_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "config",
            "personas",
        )
        available_personas = []
        if os.path.isdir(personas_dir):
            available_personas = sorted(
                [
                    f.replace(".yaml", "")
                    for f in os.listdir(personas_dir)
                    if f.endswith(".yaml")
                ]
            )

        # Read live2d config
        try:
            live2d_cfg = Live2DConfig.load()
            live2d_model_path = live2d_cfg.model.path
        except Exception as e:
            logger.warning(f"[ConfigHandlers] Failed to load Live2D config, using fallback: {e}")
            live2d_model_path = "/live2d/haru/haru_greeter_t03.model3.json"

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
                "llm": config.agent.llm_config.type
                if config.agent and config.agent.llm_config
                else None,
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
        await self.sio.emit("config_data", config_data, to=sid)

    # ── Heartbeat ──────────────────────────────────────────────────────

    async def on_heartbeat(self, sid: str, data: dict) -> None:
        """Heartbeat check."""
        await self.sio.emit("heartbeat-ack", {}, to=sid)

    # ── Translation events ────────────────────────────────────────────

    async def on_translation_configure(self, sid: str, data: dict) -> None:
        """Update translation configuration at runtime."""
        target_language = data.get("target_language")
        if target_language:
            translation_state.target_language = target_language
            logger.info(
                f"[{sid}] Translation target language updated to: {target_language}"
            )
            await self.sio.emit(
                "translation.status",
                {
                    "target_language": translation_state.target_language,
                    "enabled": translation_state.enabled,
                },
                to=sid,
            )
        else:
            await self.sio.emit(
                "translation.status",
                {
                    "target_language": translation_state.target_language,
                    "enabled": translation_state.enabled,
                },
                to=sid,
            )
