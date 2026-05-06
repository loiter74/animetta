"""Memory module data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Chunk:
    """Text chunk"""
    text: str
    path: str  # Source file relative path
    source: str  # "memory" | "daily" | "session"
    start_line: int
    end_line: int
    content_hash: str  # SHA-256, for deduplication and caching
    chunk_index: int  # Sequence number within file
    oral_version: str | None = None  # Colloquial version (optional)


@dataclass
class FileEntry:
    """File index entry"""
    path: str
    source: str
    file_hash: str  # Full file content hash
    indexed_at: float  # timestamp
    chunk_count: int


@dataclass
class SearchResult:
    """Search result"""
    text: str
    path: str
    start_line: int
    end_line: int
    score: float  # Fused final score [0, 1]
    source: str
    vector_score: float = 0.0
    keyword_score: float = 0.0
    oral_version: str | None = None  # Colloquial version (if available)


@dataclass
class MemoryFlushSignal:
    """Flush signal before context compression."""

    current_tokens: int
    context_window: int
    message: str = "Session nearing compaction. Store durable memories now."
