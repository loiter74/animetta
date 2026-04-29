"""
记忆系统 - Wiki 架构 (Karpathy-style)

目录约定:
- raw/     不可变的原始对话日志
- wiki/    AI 维护的知识库
  - entities/   人物、角色、项目
  - concepts/   偏好、兴趣、模式
  - sources/    每日对话摘要
  - synthesis/  跨源综合分析
  - index.md    总目录
  - log.md      操作日志

底层存储: SQLite FTS5 + Chroma 向量 + Markdown 文件
"""

# 核心入口
from .models.turns import MemoryTurn
from .system import MemorySystem

# 底层存储组件
from .config import MemoryConfig, ChunkConfig, SearchConfig, EmbeddingConfig
from .manager import MemoryManager
from .models.base import SearchResult, Chunk, FileEntry, MemoryFlushSignal
from .tools import get_tool_schemas, execute_tool

# Wiki 架构组件
from .wiki import (
    WikiManager,
    WikiIngestor,
    WikiQuery,
    WikiLint,
    LintReport,
    WikiPage,
    PageType,
)

__all__ = [
    # 核心
    "MemoryTurn",
    "MemorySystem",
    # 底层
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
    # 工具
    "get_tool_schemas",
    "execute_tool",
]
