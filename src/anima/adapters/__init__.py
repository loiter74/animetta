"""
Adapter Layer - 通道适配器层

将外部输入（Socket.IO / REST / CLI 等）统一接入系统。

核心概念：
- ChannelAdapter: 适配器基类，负责输入/输出的双向转换
- AdapterRegistry: 适配器注册表，管理所有活跃的适配器实例

数据流：
    外部输入 → Adapter → Orchestrator.process_input()
    Orchestrator → EventBus → Adapter.send() → 外部客户端
"""

from .base import (
    ChannelAdapter,
    AdapterCapabilities,
)
from .registry import AdapterRegistry

# 导入实现（按需导入，避免循环依赖）
from .implementations import DesktopLive2DChatter, DesktopChatterConfig

__all__ = [
    # Base classes
    'ChannelAdapter',
    'AdapterCapabilities',
    # Registry
    'AdapterRegistry',
    # Implementations
    'DesktopLive2DChatter',
    'DesktopChatterConfig',
]
