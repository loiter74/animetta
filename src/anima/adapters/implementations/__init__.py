"""
Adapter Implementations - 适配器实现

提供各种通道的适配器实现。

已实现的适配器：
- DesktopLive2DChatter: Electron 桌面应用（Live2D + 语音/文本聊天）

注意：AudioBufferManager 已统一到 anima.state 模块
"""

from .desktop_live2d_chatter import (
    DesktopLive2DChatter,
    DesktopChatterConfig,
)

__all__ = [
    'DesktopLive2DChatter',
    'DesktopChatterConfig',
]

