"""
事件系统模块

包含事件总线、事件路由和事件模型
"""

from .bus import EventBus, EventPriority, Subscription
from .router import EventRouter
from .models import (
    # 基础类型
    EventType,
    ControlSignal,
    OutputEvent,
    SinkMessage,

    # Adapter Layer 类型
    ChannelMessage,
    ChannelInfo,

    # MCP Layer 类型
    ToolPermission,
    ToolCallRequest,
    ToolCallResult,
    ToolSchema,
)

__all__ = [
    # 基础
    'EventBus',
    'EventPriority',
    'Subscription',
    'EventRouter',
    'EventType',
    'ControlSignal',
    'OutputEvent',
    'SinkMessage',

    # Adapter Layer
    'ChannelMessage',
    'ChannelInfo',

    # MCP Layer
    'ToolPermission',
    'ToolCallRequest',
    'ToolCallResult',
    'ToolSchema',
]
