"""Meme data models — shared models extracted from memory/meme for neutral access."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class MemeSource(StrEnum):
    AI = "ai"          # AI-discovered via PeriodicLearner
    USER = "user"      # User-configured via frontend


@dataclass
class CognitiveAnalysis:
    """LLM 认知分析结果 — 梗的幽默机制、使用场景、情感色彩等结构化描述."""

    humor_mechanism: str = ""          # "双关", "反讽", "荒诞", "自指", "谐音", "反差"
    context_trigger: str = ""          # 触发场景描述
    emotional_tone: str = ""           # "幽默", "讽刺", "自嘲", "温暖", "荒诞"
    persona_fit_score: float = 0.5     # 0-1 与当前人设的匹配度
    usage_example: str = ""            # 对话中使用示例
    source_url: str = ""               # B 站视频链接
    roast: str = ""                    # AI 反馈（赞赏或吐槽）

    def to_dict(self) -> dict:
        return {
            "humor_mechanism": self.humor_mechanism,
            "context_trigger": self.context_trigger,
            "emotional_tone": self.emotional_tone,
            "persona_fit_score": self.persona_fit_score,
            "usage_example": self.usage_example,
            "source_url": self.source_url,
            "roast": self.roast,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> CognitiveAnalysis | None:
        if data is None:
            return None
        return cls(
            humor_mechanism=data.get("humor_mechanism", ""),
            context_trigger=data.get("context_trigger", ""),
            emotional_tone=data.get("emotional_tone", ""),
            persona_fit_score=data.get("persona_fit_score", 0.5),
            usage_example=data.get("usage_example", ""),
            source_url=data.get("source_url", ""),
            roast=data.get("roast", ""),
        )


@dataclass
class Meme:
    """A single meme (梗) in the pool."""

    id: str = ""
    text: str = ""                        # 梗文本
    context_hint: str = ""                # 适合使用的上下文描述
    source: MemeSource = MemeSource.AI
    tags: list[str] = field(default_factory=list)
    base_score: float = 0.7               # 基础分（不衰减）
    current_score: float = 0.7            # 当前分（随时间衰减）
    use_count: int = 0
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    is_active: bool = True                # True = 在活跃池中
    resurrection_count: int = 0           # 复活次数
    cognitive_analysis: CognitiveAnalysis | None = None  # LLM 认知分析结果
    source_platform: str = "internal"     # "internal" | "bilibili" | "user"
    review_status: str = "pending"        # "pending" | "good" | "bad"

    def __post_init__(self):
        if not self.id:
            short = uuid.uuid4().hex[:8]
            self.id = f"meme_{short}"
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> dict:
        result = {
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
            "source_platform": self.source_platform,
            "review_status": self.review_status,
        }
        if self.cognitive_analysis:
            result["cognitive_analysis"] = self.cognitive_analysis.to_dict()
        return result
