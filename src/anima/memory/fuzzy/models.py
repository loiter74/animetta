"""Data models for fuzzy memory system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Granularity(str, Enum):
    """粒度: 模糊记忆的抽象级别."""
    FACT = "fact"        # 事实级: "用户喜欢 TypeScript"
    PERSONA = "persona"  # 画像级: "用户是上海的程序员，养猫"
    EVENT = "event"      # 事件级: "上周用户聊到去杭州旅游"


@dataclass
class FuzzyMemory:
    """A fuzzy human-like memory entry.

    Stores narrative-format recall with reference to source exact memories.
    """

    id: str = ""
    session_id: str = ""
    text: str = ""                       # "我记得用户说过喜欢 TypeScript 的函数式风格"
    granularity: Granularity = Granularity.EVENT
    confidence: float = 0.7              # LLM confidence score 0.0-1.0
    source_turn_ids: List[str] = field(default_factory=list)  # references to exact MemoryTurns
    created_at: Optional[datetime] = None
    last_injected_at: Optional[datetime] = None
    injection_count: int = 0

    def __post_init__(self):
        if not self.id:
            short = uuid.uuid4().hex[:12]
            self.id = f"fuzzy_{short}"
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "text": self.text,
            "granularity": self.granularity.value,
            "confidence": self.confidence,
            "source_turn_ids": self.source_turn_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_injected_at": self.last_injected_at.isoformat() if self.last_injected_at else None,
            "injection_count": self.injection_count,
        }


@dataclass
class InvertedIndexEntry:
    """Maps a fuzzy memory to its exact source record."""

    fuzzy_id: str = ""
    exact_type: str = ""         # 'memory_turn' | 'memory_entry' | 'wiki_page'
    exact_id: str = ""           # the exact record identifier
    relevance: float = 1.0       # how relevant this exact memory is to the fuzzy one

    def to_dict(self) -> dict:
        return {
            "fuzzy_id": self.fuzzy_id,
            "exact_type": self.exact_type,
            "exact_id": self.exact_id,
            "relevance": self.relevance,
        }
