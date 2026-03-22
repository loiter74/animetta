"""WebSocket 服务器 - Socket.IO 服务器初始化和配置"""

import os
import sys
from pathlib import Path
from typing import Optional

import socketio
from loguru import logger

from .session import SessionManager
from .routes import register_routes, RouteHandlers
from .lifecycle import LifecycleManager
from .desktop import DesktopClientManager
from .live2d import Live2DManager


class WebSocketServer:
    """WebSocket 服务器"""

    def __init__(self, config=None):
        """初始化 WebSocket 服务器"""
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

        self.asgi_app = socketio.ASGIApp(self.sio)
        self.session_manager = SessionManager()
        self.desktop_manager = DesktopClientManager()
        self.live2d_manager = Live2DManager()
        self.lifecycle = LifecycleManager()
        self.route_handlers: Optional[RouteHandlers] = None

        logger.info(f"[Socket.IO] Server created with async_mode='asgi'")
        logger.info(f"[Socket.IO] CORS enabled: origins=*")

    def set_config(self, config) -> None:
        """设置应用配置"""
        self.config = config
        if self.route_handlers:
            self.route_handlers.set_global_config(config)

    def set_user_settings(self, user_settings) -> None:
        """设置用户设置"""
        if self.route_handlers:
            self.route_handlers.set_user_settings(user_settings)

    def setup_routes(self) -> None:
        """设置所有路由"""
        self.route_handlers = register_routes(
            self.sio,
            self.session_manager,
            self.desktop_manager,
            self.live2d_manager
        )
        logger.info("WebSocket 路由已注册")

    def setup_lifecycle(self) -> None:
        """设置生命周期管理"""
        import asyncio

        shutdown_event = asyncio.Event()
        self.lifecycle.setup_signal_handlers(shutdown_event)
        self.lifecycle.register_cleanup_callback(self._cleanup_all_resources)
        logger.info("生命周期管理器已设置")

    async def _cleanup_all_resources(self) -> None:
        """清理所有资源"""
        logger.info("开始清理所有资源...")
        await self.session_manager.cleanup_all()
        logger.info("所有资源已清理完成")

    def get_app(self):
        """获取 ASGI 应用"""
        return self.asgi_app

    async def start(self) -> None:
        """启动服务器"""
        self.setup_routes()
        self.setup_lifecycle()
        logger.info("WebSocket 服务器已启动")

    async def stop(self) -> None:
        """停止服务器"""
        await self._cleanup_all_resources()
        logger.info("WebSocket 服务器已停止")


def create_server(config=None) -> WebSocketServer:
    """创建 WebSocket 服务器实例"""
    server = WebSocketServer(config)
    server.setup_routes()
    server.setup_lifecycle()
    return server
