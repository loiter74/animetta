"""
记忆系统

基于 OpenClaw 架构的新版记忆系统：
- Markdown 文件是唯一事实来源 (MEMORY.md + daily logs)
- 混合检索: 向量语义搜索 (70%) + BM25 关键词搜索 (30%)
- 滑动窗口分块: ~400 token/块, 80 token 重叠
- 增量索引: 基于文件哈希检测变更

架构:
    config.py          - 配置项 (ChunkConfig, SearchConfig, MemoryConfig)
    models.py          - 数据模型 (Chunk, FileEntry, SearchResult)
    chunker.py         - Markdown 分块算法
    sqlite_store.py    - SQLite FTS5 + 元数据存储
    chroma_store.py    - Chroma 向量存储
    hybrid_search.py   - 混合检索 (向量 + 关键词加权融合)
    memory_manager.py  - 核心管理器 (索引/同步/搜索)
    memory_system.py   - 统一入口 (兼容旧接口)
    memory_turn.py     - 对话轮次数据模型
    tools.py           - Agent 工具接口 (memory_search / memory_get)
"""

# 核心类
from .models.turns import MemoryTurn
from .system import MemorySystem

# 新版记忆系统组件
from .config import MemoryConfig, ChunkConfig, SearchConfig, EmbeddingConfig
from .manager import MemoryManager
from .models.base import SearchResult, Chunk, FileEntry, MemoryFlushSignal
from .tools import get_tool_schemas, execute_tool

__all__ = [
    # 兼容旧接口
    "MemoryTurn",
    "MemorySystem",
    # 新版组件
    "MemoryConfig",
    "ChunkConfig",
    "SearchConfig",
    "EmbeddingConfig",
    "MemoryManager",
    "SearchResult",
    "Chunk",
    "FileEntry",
    "MemoryFlushSignal",
    # Agent 工具
    "get_tool_schemas",
    "execute_tool",
]
