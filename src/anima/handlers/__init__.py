"""
事件处理器模块

包含所有事件处理器的基础类和实现，以及统一的注册中心。
"""

from .base import BaseHandler
from .text import TextHandler
from .unified import UnifiedEventHandler
from .input_handler import InputHandler
from .registry import HandlerRegistry, HandlerConfig

__all__ = [
    'BaseHandler',
    'TextHandler',
    'UnifiedEventHandler',
    'InputHandler',
    'HandlerRegistry',
    'HandlerConfig',
]
