"""Memory entry data models - MemoryEntry + MemoryRelation"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class RelationType(str, Enum):
    """Memory relation type"""
    UPDATES = "updates"    # New memory replaces old memory
    EXTENDS = "extends"    # New memory extends/supplements old memory
    DERIVES = "derives"    # Memory derives from some source


@dataclass
class MemoryEntry:
    """
    Memory entry

    - References OpenClaw's MemoryEntry design
    - Supports version chain: root_memory_id → parent_memory_id → id
    - Supports soft delete: is_forgotten
    """

    id: str                           # UUID
    memory: str                       # Fact text (e.g. "User likes TypeScript")
    space_id: str                     # Container ID (conversation scope)
    version: int = 1                  # Version number, incremented on each update
    is_latest: bool = True            # Whether this is the latest version
    is_static: bool = False           # Long-term vs short-term memory
    is_forgotten: bool = False        # Soft delete/forget
    forget_after: Optional[str] = None  # ISO datetime, auto-expiration time
    parent_memory_id: Optional[str] = None  # ID of the old version replaced by this one
    root_memory_id: Optional[str] = None   # Version chain root ID, first version points to itself
    confidence: float = 1.0           # Confidence [0.0, 1.0]
    created_at: Optional[str] = None  # ISO datetime
    updated_at: Optional[str] = None  # ISO datetime


@dataclass
class MemoryRelation:
    """
    Memory relation

    Represents the semantic relationship between two MemoryEntry objects.
    """

    source_id: str                 # Source memory ID
    target_id: str                 # Target memory ID
    relation: RelationType         # Relation type
    created_at: Optional[str] = None  # ISO datetime
