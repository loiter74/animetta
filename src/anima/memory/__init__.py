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

# Core entry point
from .models.turns import MemoryTurn
from .system import MemorySystem

# Backend storage components
from .config import MemoryConfig, ChunkConfig, SearchConfig, EmbeddingConfig
from .manager import MemoryManager
from .models.base import SearchResult, Chunk, FileEntry, MemoryFlushSignal
from .tools import get_tool_schemas, execute_tool

# Wiki architecture components
from .wiki import (
    WikiManager,
    WikiIngestor,
    WikiQuery,
    WikiLint,
    LintReport,
    WikiPage,
    PageType,
)

# Memory Evolution (new: FuzzyLayer replaces FuzzyMemoryStore)
from .fuzzy_layer import FuzzyLayer

__all__ = [
    # Core
    "MemoryTurn",
    "MemorySystem",
    # Backend
    "MemoryConfig",
    "ChunkConfig",
    "SearchConfig",
    "EmbeddingConfig",
    "MemoryManager",
    "SearchResult",
    "Chunk",
    "FileEntry",
    "MemoryFlushSignal",
    # Wiki
    "WikiManager",
    "WikiIngestor",
    "WikiQuery",
    "WikiLint",
    "LintReport",
    "WikiPage",
    "PageType",
    # Tools
    "get_tool_schemas",
    "execute_tool",
    # Memory Evolution
    "FuzzyMemory",
    "FuzzyMemoryStore",
    "FuzzyConsolidator",
    "FuzzyLayer",
    "PeriodicLearner",
    "Meme",
    "MemeStore",
    "MemePool",
]
