"""
Server module

Contains WebSocket server, session management, route handling and lifecycle management
"""

from .websocket import WebSocketServer, create_server
from .session import SessionManager
from .routes import RouteHandlers, register_routes
from .lifecycle import LifecycleManager
from .desktop import DesktopClientManager, DESKTOP_CLIENT_TYPES
from .live2d import Live2DManager

__all__ = [
    # Server
    'WebSocketServer',
    'create_server',
    # Session management
    'SessionManager',
    # Routes
    'RouteHandlers',
    'register_routes',
    # Lifecycle
    'LifecycleManager',
    # Desktop client
    'DesktopClientManager',
    'DESKTOP_CLIENT_TYPES',
    # Live2D
    'Live2DManager',
]
