"""记忆条目数据模型 - MemoryEntry + MemoryRelation"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class RelationType(str, Enum):
    """记忆关系类型"""
    UPDATES = "updates"    # 新记忆取代了旧记忆
    EXTENDS = "extends"    # 新记忆扩展/补充了旧记忆
    DERIVES = "derives"    # 记忆衍生自某个来源


@dataclass
class MemoryEntry:
    """原子事实级记忆单元.

    表示一个原子事实，带版本链，可追溯事实演变。
    """

    id: str                           # UUID
    memory: str                       # 事实文本 (如 "用户喜欢 TypeScript")
    space_id: str                     # 容器 ID (对话范围)
    version: int = 1                  # 版本号，每次更新 +1
    is_latest: bool = True            # 是否为最新版本
    is_static: bool = False           # 长期 vs 短期记忆
    is_forgotten: bool = False        # 软删除/遗忘
    forget_after: Optional[str] = None  # ISO datetime, 自动过期时间
    parent_memory_id: Optional[str] = None  # 被此版本取代的旧版 ID
    root_memory_id: Optional[str] = None   # 版本链根 ID, 首版为自身 ID
    confidence: float = 1.0           # 置信度 [0.0, 1.0]
    created_at: Optional[str] = None  # ISO datetime
    updated_at: Optional[str] = None  # ISO datetime


@dataclass
class MemoryRelation:
    """记忆关系记录.

    表示两个 MemoryEntry 之间的语义关系.
    """

    source_id: str                 # 源记忆 ID
    target_id: str                 # 目标记忆 ID
    relation: RelationType         # 关系类型
    created_at: Optional[str] = None  # ISO datetime
