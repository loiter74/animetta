"""
Live streaming platform services.

Re-exported from services.bilibili after consolidation.
Keep this shim for backward compatibility — new code should import from services.bilibili directly.
"""

from animetta.services.bilibili import DanmakuService, DanmakuMessage, DanmakuReply

__all__ = [
    "DanmakuService",
    "DanmakuMessage",
    "DanmakuReply",
]
