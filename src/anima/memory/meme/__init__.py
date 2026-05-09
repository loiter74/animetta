"""MemePool — 梗管理系统.

Manages a pool of 10 active memes (梗) with lifecycle:
Generate → Store → Inject → Score → Discard/Resurrect (time-decay).
80% AI-discovered + 20% user-configured.
"""

from .models import Meme, MemeSource
from .store import MemeStore
from .engine import MemePool

__all__ = [
    "Meme",
    "MemeSource",
    "MemeStore",
    "MemePool",
]
