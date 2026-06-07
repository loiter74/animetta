"""B站热梗情报服务 — 定期采集 B站热门视频、评论、弹幕，识别新兴梗模式.

Re-exported from services.bilibili after consolidation.
Keep this shim for backward compatibility — new code should import from services.bilibili directly.

MemeCognitiveAnalyzer (analyzer.py) remains local — it is platform-agnostic.
"""

from animetta.services.bilibili import DanmakuBuffer, DanmakuPhrase

__all__ = [
    "DanmakuBuffer",
    "DanmakuPhrase",
]
