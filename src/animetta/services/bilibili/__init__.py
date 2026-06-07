"""Bilibili danmaku service package — live chat, meme collection, interaction learning.

Provides:
    DanmakuService      — WebSocket-based live danmaku listener
    MemeCollector       — Trending video + comment collection + meme identification
    InteractionLearner  — Danmaku interaction pattern analysis + strategy generation
    DanmakuBuffer       — Ring buffer for real-time danmaku phrase tracking
"""

from .danmaku_buffer import DanmakuBuffer, DanmakuPhrase
from .danmaku_service import DanmakuService, DanmakuMessage, DanmakuReply
from .interaction_learner import InteractionLearner
from .meme_collector import MemeCollector, CollectedVideo, CollectedComment, MemeCandidate
from .models import InteractionPattern, LivestreamStrategy

__all__ = [
    "DanmakuService",
    "DanmakuMessage",
    "DanmakuReply",
    "DanmakuBuffer",
    "DanmakuPhrase",
    "MemeCollector",
    "CollectedVideo",
    "CollectedComment",
    "MemeCandidate",
    "InteractionLearner",
    "InteractionPattern",
    "LivestreamStrategy",
]
