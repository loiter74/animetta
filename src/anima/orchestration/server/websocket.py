"""WebSocket server - Socket.IO server initialization and configuration"""

import os
import sys
from pathlib import Path
from typing import Optional

import socketio
from loguru import logger
from starlette.applications import Starlette
from starlette.routing import Mount

from .session import SessionManager
from .routes import register_routes, RouteHandlers
from .lifecycle import LifecycleManager
from .desktop import DesktopClientManager
from .live2d import Live2DManager
from .stats_api import get_stats_routes
from anima.core.model_loading_manager import ModelLoadingManager
from anima.tracing import init_tracing


class WebSocketServer:
    """WebSocket server"""

    def __init__(self, config=None):
        """Initialize WebSocket server"""
        self.config = config

        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',
            cors_credentials=True,
            logger=False,
            engineio_logger=False,
            ping_timeout=120,
            ping_interval=30,
        )

        # Socket.IO ASGI + Stats API routes
        sio_app = socketio.ASGIApp(self.sio)
        stats_routes = get_stats_routes()

        self.asgi_app = Starlette(
            routes=stats_routes + [Mount("/", app=sio_app)],
        )
        self.model_manager = ModelLoadingManager()
        self.session_manager = SessionManager(model_manager=self.model_manager)
        self.desktop_manager = DesktopClientManager()
        self.live2d_manager = Live2DManager()
        self.lifecycle = LifecycleManager()
        self.route_handlers: Optional[RouteHandlers] = None

        logger.info(f"[Socket.IO] Server created with async_mode='asgi'")
        logger.info(f"[Socket.IO] CORS enabled: origins=*")

    def set_config(self, config) -> None:
        """Set application config"""
        self.config = config
        if self.route_handlers:
            self.route_handlers.set_global_config(config)

    def set_user_settings(self, user_settings) -> None:
        """Set user settings"""
        if self.route_handlers:
            self.route_handlers.set_user_settings(user_settings)

    def setup_tracing(self) -> None:
        """Initialize OpenTelemetry tracing pipeline."""
        init_tracing()

    async def prewarm_services(self) -> None:
        """Pre-warm service imports and model loading at server startup.

        Initializes the global ServicePool so that the first user request
        reuses the already-loaded LLM/TTS/ASR engines instead of creating
        them from scratch.
        """
        if self.config is None:
            logger.info("[Prewarm] No config loaded yet, skipping")
            return

        from anima.core.service_pool import ServicePool
        await ServicePool.init(self.config, model_manager=self.model_manager)

    def setup_routes(self) -> None:
        """Set up all routes"""
        self.route_handlers = register_routes(
            self.sio,
            self.session_manager,
            self.desktop_manager,
            self.live2d_manager
        )

        # Wire up model manager with Socket.IO for status events
        self.model_manager._socketio = self.sio

        logger.info("WebSocket routes registered")

    def setup_lifecycle(self) -> None:
        """Set up lifecycle management"""
        import asyncio

        shutdown_event = asyncio.Event()
        self.lifecycle.setup_signal_handlers(shutdown_event)
        self.lifecycle.register_cleanup_callback(self._cleanup_all_resources)
        logger.info("Lifecycle manager set up")

    async def _cleanup_all_resources(self) -> None:
        """Clean up all resources"""
        logger.info("Starting to clean up all resources...")
        await self.session_manager.cleanup_all()
        logger.info("All resources cleaned up")

    def get_app(self):
        """Get the ASGI app"""
        return self.asgi_app

    async def start(self) -> None:
        """Start the server"""
        self.setup_routes()
        self.setup_lifecycle()
        logger.info("WebSocket server started")

    async def stop(self) -> None:
        """Stop the server"""
        await self._cleanup_all_resources()
        logger.info("WebSocket server stopped")


def create_server(config=None) -> WebSocketServer:
    """Create a WebSocket server instance"""
    server = WebSocketServer(config)
    server.setup_tracing()
    server.setup_routes()
    server.setup_lifecycle()
    return server
