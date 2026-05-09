"""MemePool data models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MemeSource(str, Enum):
    AI = "ai"          # AI-discovered via PeriodicLearner
    USER = "user"      # User-configured via frontend


@dataclass
class Meme:
    """A single meme (梗) in the pool."""

    id: str = ""
    text: str = ""                        # 梗文本
    context_hint: str = ""                # 适合使用的上下文描述
    source: MemeSource = MemeSource.AI
    tags: List[str] = field(default_factory=list)
    base_score: float = 0.7               # 基础分（不衰减）
    current_score: float = 0.7            # 当前分（随时间衰减）
    use_count: int = 0
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_active: bool = True                # True = 在活跃池中
    resurrection_count: int = 0           # 复活次数

    def __post_init__(self):
        if not self.id:
            short = uuid.uuid4().hex[:8]
            self.id = f"meme_{short}"
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "context_hint": self.context_hint,
            "source": self.source.value,
            "tags": self.tags,
            "base_score": self.base_score,
            "current_score": self.current_score,
            "use_count": self.use_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
            "resurrection_count": self.resurrection_count,
        }
