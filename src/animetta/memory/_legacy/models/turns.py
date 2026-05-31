"""Memory data model - MemoryTurn"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class MemoryTurn:
    """Single conversation turn data"""
    turn_id: str
    session_id: str
    timestamp: datetime
    user_input: str
    agent_response: str
    emotions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
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
