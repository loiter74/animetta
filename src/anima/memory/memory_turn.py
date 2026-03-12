"""
记忆数据模型

MemoryTurn - 单次对话数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class MemoryTurn:
    """
    单次对话数据

    Attributes:
        turn_id: 唯一标识符
        session_id: 会话 ID
        timestamp: 时间戳
        user_input: 用户输入
        agent_response: Agent 回复
        emotions: Live2D 表情列表
        metadata: 元数据
        importance: 重要性评分 (0-1)
    """
    turn_id: str
    session_id: str
    timestamp: datetime
    user_input: str
    agent_response: str
    emotions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input,
            "agent_response": self.agent_response,
            "emotions": self.emotions,
            "metadata": self.metadata,
            "importance": self.importance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryTurn":
        """从字典创建"""
        return cls(
            turn_id=data["turn_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            user_input=data["user_input"],
            agent_response=data["agent_response"],
            emotions=data.get("emotions", []),
            metadata=data.get("metadata", {}),
            importance=data.get("importance", 0.5),
        )
