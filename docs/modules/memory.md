# Memory System

基于 OpenClaw 架构的记忆系统，使用 **Chroma** (向量) + **SQLite** (FTS5) 实现。

---

## 核心设计

1. **Markdown 是唯一事实来源** — 所有记忆写入磁盘
2. **两层记忆**: `MEMORY.md` (长期) + `memory/YYYY-MM-DD.md` (日志)
3. **混合检索**: 向量语义搜索 (70%) + BM25 关键词搜索 (30%)
4. **滑动窗口分块**: ~400 token/块, 80 token 重叠
5. **增量索引**: 基于文件哈希检测变更

---

## 项目结构

```
src/anima/memory/
├── config.py          # 配置项
├── models.py          # 数据模型
├── chunker.py         # 分块算法
├── sqlite_store.py    # SQLite FTS5 + 元数据
├── chroma_store.py    # Chroma 向量存储
├── hybrid_search.py   # 混合检索
├── memory_manager.py  # 核心管理器
├── memory_system.py   # 统一入口
└── tools.py           # Agent 工具接口
```

---

## 快速使用

```python
from anima.memory import MemorySystem, MemoryTurn

# 初始化
memory = MemorySystem({
    "workspace_dir": "~/.anima/workspace",
    "short_term_max_turns": 20,
})

# 存储对话
turn = MemoryTurn(
    session_id="session-001",
    user_input="你好",
    agent_response="你好！有什么可以帮你的吗？",
)
await memory.store_turn(turn)

# 检索相关记忆
results = await memory.retrieve_context(
    query="用户说过什么",
    session_id="session-001",
    max_turns=5
)
```

---

## 配置说明

### MemoryConfig

| 参数 | 默认值 | 说明 |
|------|--------|------|
| workspace_dir | ~/.anima/workspace | 工作目录 |
| chunk.target_tokens | 400 | 每块目标 token 数 |
| chunk.overlap_tokens | 80 | 相邻块重叠 token 数 |
| search.vector_weight | 0.7 | 向量得分权重 |
| search.keyword_weight | 0.3 | 关键词得分权重 |

---

## 混合搜索原理

1. **向量检索**: Chroma 使用 HNSW 索引进行余弦相似度搜索
2. **关键词检索**: SQLite FTS5 使用 BM25 算法
3. **分数归一化**: 两者归一化到 [0, 1]
4. **加权融合**: `final = 0.7 * vector + 0.3 * keyword`

---

## 依赖

```bash
pip install chromadb sentence-transformers
```

---

## 文件结构

```
workspace/
├── MEMORY.md           # 长期记忆
└── memory/
    ├── 2026-03-13.md   # 每日日志
    └── ...
```
