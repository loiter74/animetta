# Memory System

基于 OpenClaw 架构的新版记忆系统，使用 **Chroma** (向量数据库) + **SQLite** (FTS5 关键词搜索 + 元数据) 实现的 Python 记忆模块。

## 核心设计理念

1. **Markdown 文件是唯一事实来源** — 所有记忆以 Markdown 写入磁盘
2. **两层记忆**: `MEMORY.md` (长期) + `memory/YYYY-MM-DD.md` (日志)
3. **混合检索**: 向量语义搜索 (70%) + BM25 关键词搜索 (30%)
4. **滑动窗口分块**: ~400 token/块, 80 token 重叠
5. **增量索引**: 基于文件哈希检测变更，只重建有改动的文件
6. **上下文压缩前自动 flush**: 会话即将被截断前，提醒保存重要记忆

## 项目结构

```
src/anima/memory/
├── config.py          # 配置项 (ChunkConfig, SearchConfig, MemoryConfig)
├── models.py          # 数据模型 (Chunk, FileEntry, SearchResult)
├── chunker.py         # Markdown 分块算法
├── sqlite_store.py    # SQLite FTS5 + 元数据存储
├── chroma_store.py    # Chroma 向量存储
├── hybrid_search.py   # 混合检索 (向量 + 关键词加权融合)
├── memory_manager.py  # 核心管理器 (索引/同步/搜索)
├── memory_system.py   # 统一入口 (兼容旧接口)
├── memory_turn.py     # 对话轮次数据模型
└── tools.py           # Agent 工具接口 (memory_search / memory_get)
```

## 快速使用

### 基础用法

```python
from anima.memory import MemorySystem

# 初始化记忆系统
memory = MemorySystem({
    "workspace_dir": "~/.anima/workspace",
    "short_term_max_turns": 20,
})

# 存储对话
from anima.memory import MemoryTurn
from datetime import datetime

turn = MemoryTurn(
    turn_id="turn-001",
    session_id="session-001",
    timestamp=datetime.now(),
    user_input="你好",
    agent_response="你好！有什么可以帮你的吗？",
    emotions=["happy"],
)
await memory.store_turn(turn)

# 检索相关记忆
results = await memory.retrieve_context(
    query="用户说过什么",
    session_id="session-001",
    max_turns=5
)
```

### 直接使用 MemoryManager

```python
from anima.memory import MemoryManager, MemoryConfig

config = MemoryConfig(
    workspace_dir="~/.anima/workspace",
    embedding=EmbeddingConfig(model_name="BAAI/bge-small-zh-v1.5"),
)
mgr = MemoryManager(config)

# 写入记忆
mgr.write_memory("用户偏好 Python 3.12, 使用 ruff 做 lint")
mgr.write_daily_log("今天帮用户重构了 auth 模块")

# 搜索记忆
results = mgr.search("用户的代码风格偏好")
for r in results:
    print(f"[{r.score:.2f}] {r.path}:{r.start_line}-{r.end_line}")
    print(r.text)

# 读取特定文件
content = mgr.get("MEMORY.md", start_line=1, end_line=20)

# 加载会话上下文
context = mgr.load_session_context()
```

### Agent 工具接口

```python
from anima.memory import get_tool_schemas, execute_tool

# 获取工具 schema (用于 function calling)
schemas = get_tool_schemas()
# 返回: [MEMORY_SEARCH_SCHEMA, MEMORY_GET_SCHEMA]

# 执行工具
result = execute_tool(mgr, "memory_search", {"query": "用户偏好", "max_results": 5})
```

## 配置说明

### MemoryConfig

```python
@dataclass
class MemoryConfig:
    workspace_dir: str = "~/.anima/workspace"
    db_path: str | None = None  # 默认 workspace_dir/memory.sqlite
    chroma_path: str | None = None  # 默认 workspace_dir/chroma_db
    agent_id: str = "default"

    chunk: ChunkConfig  # 分块参数
    search: SearchConfig  # 搜索参数
    embedding: EmbeddingConfig  # Embedding 模型

    # 记忆 flush 配置
    flush_enabled: bool = True
    flush_soft_threshold_tokens: int = 4000
    reserve_tokens_floor: int = 20000
```

### ChunkConfig

```python
@dataclass
class ChunkConfig:
    target_tokens: int = 400  # 每块目标 token 数
    overlap_tokens: int = 80  # 相邻块重叠 token 数
    chars_per_token: float = 4.0  # 粗略的字符/token 比
```

### SearchConfig

```python
@dataclass
class SearchConfig:
    vector_weight: float = 0.7  # 向量得分权重
    keyword_weight: float = 0.3  # 关键词 (BM25) 得分权重
    candidate_multiplier: int = 4  # 候选池 = max_results * multiplier
    default_max_results: int = 10
```

## 依赖

```bash
pip install chromadb sentence-transformers
```

## 文件结构

```
workspace/
├── MEMORY.md           # 长期记忆
└── memory/
    ├── 2026-03-13.md   # 每日日志
    ├── 2026-03-12.md
    └── ...
```

## 混合搜索原理

1. **向量检索**: Chroma 使用 HNSW 索引进行余弦相似度搜索
2. **关键词检索**: SQLite FTS5 使用 BM25 算法
3. **分数归一化**:
   - 向量相似度: `similarity = 1 - cosine_distance`
   - 关键词得分: `score = 1 / (1 + rank)` (rank 从 0 开始)
4. **加权融合**: `final = 0.7 * vector_score + 0.3 * keyword_score`

## 与旧版对比

| 特性 | 旧版 | 新版 |
|------|------|------|
| 存储格式 | SQLite (memories 表) | Markdown 文件 + SQLite + Chroma |
| 搜索方式 | FTS5 全文搜索 | 混合搜索 (向量 + 关键词) |
| 分块策略 | 无 | 滑动窗口 (~400 token/块) |
| 增量索引 | 无 | 基于文件哈希 |
| 上下文加载 | 最近 N 轮 | MEMORY.md + 今天/昨天日志 |
| flush 提醒 | 无 | 上下文压缩前自动提醒 |
