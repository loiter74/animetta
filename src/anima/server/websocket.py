"""
WebSocket 服务器
封装 Socket.IO 服务器初始化和配置
整合 Adapter 架构和 EventBus
"""

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
    """
    WebSocket 服务器

    负责：
    1. Socket.IO 服务器初始化
    2. 会话管理
    3. 路由注册
    4. 生命周期管理
    5. 桌面客户端支持
    6. Live2D 动作队列
    """

    def __init__(self, config=None):
        """
        初始化 WebSocket 服务器

        Args:
            config: 应用配置（可选，后续可通过 set_config 设置）
        """
        self.config = config

        # 创建 Socket.IO 服务器
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',
            cors_credentials=True,
            logger=False,  # Disable default logging (we handle our own)
            engineio_logger=False,  # Disable default engine.io logging
            # 增加 ping 超时配置以提高稳定性
            ping_timeout=120,  # 等待客户端 ping 响应的时间（秒）
            ping_interval=30,  # 发送 ping 的间隔（秒）
        )

        # 创建 ASGI 应用
        self.asgi_app = socketio.ASGIApp(self.sio)

        # 创建会话管理器
        self.session_manager = SessionManager()

        # 创建桌面客户端管理器
        self.desktop_manager = DesktopClientManager()

        # 创建 Live2D 管理器
        self.live2d_manager = Live2DManager()

        # 创建生命周期管理器
        self.lifecycle = LifecycleManager()

        # 路由处理器
        self.route_handlers: Optional[RouteHandlers] = None

        logger.info(f"[Socket.IO] Server created with async_mode='asgi'")
        logger.info(f"[Socket.IO] CORS enabled: origins=*")

    def set_config(self, config) -> None:
        """
        设置应用配置

        Args:
            config: AppConfig 实例
        """
        self.config = config
        if self.route_handlers:
            self.route_handlers.set_global_config(config)

    def set_user_settings(self, user_settings) -> None:
        """
        设置用户设置

        Args:
            user_settings: UserSettings 实例
        """
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

        # 创建关闭事件
        shutdown_event = asyncio.Event()
        self.lifecycle.setup_signal_handlers(shutdown_event)

        # 注册清理回调
        self.lifecycle.register_cleanup_callback(self._cleanup_all_resources)

        logger.info("生命周期管理器已设置")

    async def _cleanup_all_resources(self) -> None:
        """清理所有资源"""
        logger.info("开始清理所有资源...")

        # 清理所有会话
        await self.session_manager.cleanup_all()

        logger.info("所有资源已清理完成")

    def get_app(self):
        """获取 ASGI 应用"""
        return self.asgi_app

    async def start(self) -> None:
        """启动服务器（异步初始化）"""
        self.setup_routes()
        self.setup_lifecycle()
        logger.info("WebSocket 服务器已启动")

    async def stop(self) -> None:
        """停止服务器"""
        await self._cleanup_all_resources()
        logger.info("WebSocket 服务器已停止")


def create_server(config=None) -> WebSocketServer:
    """
    创建 WebSocket 服务器实例

    Args:
        config: 应用配置（可选）

    Returns:
        WebSocketServer: 服务器实例
    """
    server = WebSocketServer(config)
    server.setup_routes()
    server.setup_lifecycle()
    return server
