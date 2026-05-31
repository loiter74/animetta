"""
Memory System - Wiki Architecture (Karpathy-style)

Directory conventions:
- raw/     Immutable raw conversation logs
- wiki/    AI-maintained knowledge base
  - entities/   People, characters, projects
  - concepts/   Preferences, interests, patterns
  - sources/    Daily conversation summaries
  - synthesis/  Cross-source synthesis analysis
  - index.md    Master table of contents
  - log.md      Operation log

Backend storage: SQLite FTS5 + Chroma vector + Markdown files
"""

from __future__ import annotations

# Core entry point
from .models.turns import MemoryTurn

# Backend storage components
from .config import MemoryConfig, ChunkConfig, SearchConfig, EmbeddingConfig
from .models.base import SearchResult, Chunk, FileEntry, MemoryFlushSignal
from .tools import get_tool_schemas, execute_tool

# Lazy imports — tolerate failures for lightweight consumers (memory_v2)
try:
    from .system import MemorySystem
except Exception:
    MemorySystem = None  # type: ignore[assignment]

try:
    from .manager import MemoryManager
except Exception:
    MemoryManager = None  # type: ignore[assignment]

try:
    from .wiki import (
        WikiManager, WikiIngestor, WikiQuery, WikiLint,
        LintReport, WikiPage, PageType,
    )
except Exception:
    WikiManager = WikiIngestor = WikiQuery = WikiLint = None  # type: ignore[assignment]
    LintReport = WikiPage = PageType = None  # type: ignore[assignment]

try:
    from .fuzzy_layer import FuzzyLayer
except Exception:
    FuzzyLayer = None  # type: ignore[assignment]

__all__ = [
    "MemoryTurn", "MemorySystem",
    "MemoryConfig", "ChunkConfig", "SearchConfig", "EmbeddingConfig",
    "MemoryManager", "SearchResult", "Chunk", "FileEntry", "MemoryFlushSignal",
    "WikiManager", "WikiIngestor", "WikiQuery", "WikiLint",
    "LintReport", "WikiPage", "PageType",
    "get_tool_schemas", "execute_tool",
    "FuzzyLayer",
]
