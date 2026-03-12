"""记忆模块数据模型."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Chunk:
    """一个文本块."""

    text: str
    path: str  # 来源文件相对路径
    source: str  # "memory" | "daily" | "session"
    start_line: int
    end_line: int
    content_hash: str  # SHA-256, 用于去重和缓存
    chunk_index: int  # 在文件内的序号


@dataclass
class FileEntry:
    """已索引文件的元数据."""

    path: str
    source: str
    file_hash: str  # 文件整体内容哈希
    indexed_at: float  # timestamp
    chunk_count: int


@dataclass
class SearchResult:
    """搜索结果."""

    text: str
    path: str
    start_line: int
    end_line: int
    score: float  # 融合后的最终得分 [0, 1]
    source: str
    vector_score: float = 0.0
    keyword_score: float = 0.0


@dataclass
class MemoryFlushSignal:
    """上下文压缩前的 flush 信号."""

    current_tokens: int
    context_window: int
    message: str = "Session nearing compaction. Store durable memories now."
