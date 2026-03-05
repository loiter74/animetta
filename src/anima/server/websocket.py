"""
WebSocket 服务器
封装 Socket.IO 服务器初始化和配置
"""

import socketio
from fastapi import FastAPI
from loguru import logger

from .session import SessionManager
from .routes import register_routes
from .lifecycle import LifecycleManager


class WebSocketServer:
    """
    WebSocket 服务器

    负责：
    1. Socket.IO 服务器初始化
    2. FastAPI 应用初始化
    3. 路由注册
    """

    def __init__(self):
        # 创建 Socket.IO 服务器
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins=['http://localhost:3000', 'http://127.0.0.1:3000', '*'],
            cors_credentials=True,
        )

        # 创建 FastAPI 应用
        self.app = FastAPI(title="Anima - AI Virtual Companion")

        # 创建会话管理器
        self.session_manager = SessionManager()

        # 创建生命周期管理器
        self.lifecycle = LifecycleManager()

        # 路由处理器
        self.routes = None

        # 将 Socket.IO 挂载到 FastAPI
        self.socket_app = socketio.ASGIApp(self.sio, self.app)

    def setup_routes(self):
        """设置所有路由"""
        self.routes = register_routes(self.sio, self.session_manager)
        logger.info("WebSocket 路由已注册")

    def setup_lifecycle(self, shutdown_event):
        """
        设置生命周期管理

        Args:
            shutdown_event: 关闭事件
        """
        self.lifecycle.setup_signal_handlers(shutdown_event)

        # 注册清理回调
        self.lifecycle.register_cleanup_callback(self.session_manager.cleanup_all)

        logger.info("生命周期管理器已设置")

    def get_app(self):
        """获取 ASGI 应用"""
        return self.socket_app

    def get_fastapi_app(self):
        """获取 FastAPI 应用"""
        return self.app


def create_server() -> WebSocketServer:
    """
    创建 WebSocket 服务器实例

    Returns:
        WebSocketServer: 服务器实例
    """
    server = WebSocketServer()
    server.setup_routes()
    return server
