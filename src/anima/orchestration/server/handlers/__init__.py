"""
Route handler modules — extracted from routes.py by domain.

Each module contains a handler class that receives the same
infrastructure dependencies (sio, session_manager, desktop_manager,
live2d_manager, admin for shared utilities).
"""

from .admin_handlers import AdminHandlers
from .bilibili_handlers import BilibiliHandlers
from .chat_handlers import ChatHandlers
from .live2d_handlers import Live2DHandlers

__all__ = [
    "AdminHandlers",
    "BilibiliHandlers",
    "ChatHandlers",
    "Live2DHandlers",
]
