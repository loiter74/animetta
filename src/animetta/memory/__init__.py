"""
Memory System — LivingMemory V2.

Legacy modules have been moved to src/animetta/memory/_legacy/.
Active subsystems:
  - v2/       LivingMemorySystem (MemoryAtom, EmotionalField, Metabolism)
  - storage/  Chroma + SQLite drivers (reused by v2)
  - wiki/     Read-only archive / export layer
"""

from __future__ import annotations

# Only import from modules that still exist in memory/ (not _legacy/)
# Everything else uses try/except for backward compat

try:
    from .models.turns import MemoryTurn
except Exception:
    MemoryTurn = None  # type: ignore[assignment]

try:
    from .config import MemoryConfig, ChunkConfig, SearchConfig, EmbeddingConfig
except Exception:
    MemoryConfig = ChunkConfig = SearchConfig = EmbeddingConfig = None  # type: ignore[assignment]

try:
    from .models.base import SearchResult, Chunk, FileEntry, MemoryFlushSignal
except Exception:
    SearchResult = Chunk = FileEntry = MemoryFlushSignal = None  # type: ignore[assignment]

try:
    from .tools import get_tool_schemas, execute_tool
except Exception:
    get_tool_schemas = execute_tool = None  # type: ignore[assignment]

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
