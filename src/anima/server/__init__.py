"""
服务器模块

包含 WebSocket 服务器、会话管理、路由处理和生命周期管理
使用 Adapter 架构和 EventBus 进行组件通信
"""

from .websocket import WebSocketServer, create_server
from .session import SessionManager
from .routes import RouteHandlers, register_routes
from .lifecycle import LifecycleManager
from .desktop import DesktopClientManager, DESKTOP_CLIENT_TYPES
from .live2d import Live2DManager

__all__ = [
    # 服务器
    'WebSocketServer',
    'create_server',
    # 会话管理
    'SessionManager',
    # 路由
    'RouteHandlers',
    'register_routes',
    # 生命周期
    'LifecycleManager',
    # 桌面客户端
    'DesktopClientManager',
    'DESKTOP_CLIENT_TYPES',
    # Live2D
    'Live2DManager',
]
