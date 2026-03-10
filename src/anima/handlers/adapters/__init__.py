"""
事件适配器模块

提供事件格式转换工具，用于适配前端和后端的事件格式差异。
"""

from .socket import SocketEventAdapter

__all__ = ['SocketEventAdapter']
