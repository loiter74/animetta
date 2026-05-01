# Supermemory 架构分析 & Anima 对比报告

> 日期: 2026-05-01
> 背景: 分析 supermemoryai/supermemory (MIT) 的架构，与 Anima 现有记忆系统对比，找出可借鉴点

---

## 一、Supermemory 架构全景

```
用户 <-> AI Tool (Claude/Cursor/...) <-> Supermemory MCP/Middleware <-> Backend API
                                            ↓
                                     PostgreSQL + pgvector
                                     (embeddings + memory entries)
```

### Monorepo 结构 (Turborepo + Bun)

**应用层:**
- `apps/web/` — Next.js + OpenNext + Cloudflare (用户 Dashboard + Nova AI 助手)
- `apps/mcp/` — Cloudflare Worker (MCP 协议服务器，暴露 memory/recall/context 工具)
- `apps/browser-extension/` — Chrome 插件 (WXT 框架)
- `apps/raycast-extension/` — Raycast 扩展
- `apps/docs/` — Mintlify 文档站

**核心包:**
- `packages/tools/` — SDK 核心 (npm `supermemory` 包的全部逻辑)
- `packages/validation/` — Zod Schema 定义 (数据模型单一真相来源)
- `packages/memory-graph/` — Canvas 力导向图可视化
- `packages/ui/` — shadcn/ui 组件库
- `packages/ai-sdk/` — Vercel AI SDK 集成
- `packages/openai-sdk-python/` — Python OpenAI 中间件

### 核心数据模型

```
Space (容器, containerTag 隔离多租户)
  ├── Document (文档/来源)
  │   ├── type: pdf | tweet | google_doc | image | video | webpage | ...
  │   ├── Chunk[] (分块 + 嵌入向量)
  │   └── processingMetadata (多步骤管道状态机)
  └── MemoryEntry (记忆条目 — 最核心)
      ├── memory: string           ← 提炼后的事实表述
      ├── version: number          ← 版本号 (递增)
      ├── isLatest: boolean        ← 是否为最新版
      ├── isStatic: boolean        ← 长期 vs 短期
      ├── isForgotten: boolean     ← 软删除/遗忘
      ├── forgetAfter: Date        ← 自动过期时间
      ├── parentMemoryId / rootMemoryId  ← 版本链
      └── memoryRelations: Map<id, relation>
           ├── "updates"   ← 取代了哪个旧记忆
           ├── "extends"   ← 扩展了哪个记忆
           └── "derives"   ← 衍生自哪个来源
```

### SDK 中间件模式

这是 Supermemory 最巧妙的设计：

```
LLM 调用
  │
  ├── 前处理: transformParamsWithMemory()
  │   ├── 1. 获取 User Profile (静态+动态)
  │   ├── 2. 语义搜索相关记忆
  │   ├── 3. 组装成 prompt 注入到 system message
  │   └── 4. 缓存本轮结果 (避免 tool call 重复请求)
  │
  ├── LLM 响应...
  │
  └── 后处理: saveMemoryAfterResponse()
      ├── 结构化对话 → 调 /v4/conversations (smart diffing)
      └── 后端自动解析、提取事实、建版本链
```

三种模式: `profile` (最快), `query` (语义搜索), `full` (两者结合)

---

## 二、Anima 现有记忆系统

```
MemorySystem
├── ShortTermMemory (短期记忆)
│   └── 内存 FIFO deque, 每会话 max 20 轮
├── MemoryManager (长期存储)
│   ├── SQLite FTS5   → 文件元数据 + BM25 全文搜索
│   ├── ChromaDB      → 语义向量搜索 (余弦距离)
│   └── sentence-transformers → 本地 embedding
└── WikiManager (知识库)
    ├── raw/          → 不可变对话日志
    └── wiki/         → entities / concepts / sources / synthesis
```

### 已有能力清单

| 模块 | 能力 | 实现文件 |
|------|------|---------|
| 混合搜索 | 向量 70% + BM25 30% 加权融合 | `search/hybrid.py` |
| 增量索引 | SHA-256 哈希检测，只重建变更文件 | `manager.py:_index_file()` |
| 滑动窗口分块 | 400 token/块，80 token 重叠 | `models/chunks.py` |
| Embedding 缓存 | 按内容哈希缓存，避免重复计算 | `storage/sqlite.py` (embedding_cache 表) |
| LLM 工具接口 | `memory_search` + `memory_get` function calling | `tools.py` |
| Wiki 架构 | Karpathy 风格 raw/ + wiki/ | `wiki/` 整套 |
| 上下文压缩信号 | `should_flush()` 检测 token 压力 | `manager.py` |
| 口语化记忆 | 第一人称口语化转换 prompt | `prompts.py` |
| 短期记忆 | 每会话 FIFO deque，纯内存操作 | `stores/short_term.py` |
| Chroma 向量存储 | 余弦距离，按路径删除，手动传 embedding | `storage/chroma.py` |
| SQLite FTS5 | BM25 关键词搜索，自动同步触发器 | `storage/sqlite.py` |

---

## 三、能力对比矩阵

| 能力维度 | Supermemory | Anima | 差距分析 |
|----------|------------|-------|---------|
| **混合搜索** | 向量 + 关键词 | ✅ 向量 + BM25 FTS5 | 基本持平 |
| **增量索引** | 隐式 (后端处理) | ✅ SHA-256 哈希检测 | Anima 更透明 |
| **事实粒度记忆** | ✅ MemoryEntry 版本链 | ❌ 只存 chunk 级文本 | **核心差距** |
| **版本链/矛盾解决** | ✅ version + isLatest + parentMemoryId | ❌ 旧值直接覆盖 | **核心差距** |
| **User Profile** | ✅ static + dynamic 双轨, ~50ms | ❌ 无 | **大差距** |
| **自动事实抽取** | ✅ 后端自动从对话提取 | ❌ 只存整段对话 | **大差距** |
| **中间件自动注入** | ✅ 拦截 LLM 调用，自动注入 system prompt | ⚠️ 需 Agent 显式 tool call | **中差距** |
| **记忆关系** | ✅ updates / extends / derives 三类型 | ❌ 无关系追踪 | **中差距** |
| **自动遗忘/过期** | ✅ forgetAfter + isForgotten | ❌ 无 TTL 机制 | **中差距** |
| **Per-turn 缓存** | ✅ MemoryCache 按 turnKey 去重 | ❌ 每次 tool call 都检索 | **小差距** |
| **MCP 协议** | ✅ 标准 MCP Server | ⚠️ 已有 MCP 工具注册 | 可扩展 |
| **记忆图可视化** | ✅ Canvas 力导向图 (开源) | ❌ 无 | 锦上添花 |
| **多框架集成** | ✅ Vercel AI SDK / LangChain / Mastra / OpenAI SDK | ⚠️ 仅有 function calling | 场景不同 |

---

## 四、推荐借鉴优先级

### P0 — 最高价值，中等实现成本

#### 1. 事实级版本化记忆

当前: Anima 以 chunk 为单位存文本，新内容直接覆盖旧索引。
目标: 引入 MemoryEntry 概念，以原子事实为单位，带版本链。

**设计方案:**
- SQLite 新增 `memory_entries` 表:

```sql
CREATE TABLE memory_entries (
    id          TEXT PRIMARY KEY,         -- UUID
    memory      TEXT NOT NULL,            -- 事实文本
    space_id    TEXT NOT NULL,            -- 容器 (类似 containerTag)
    is_latest   INTEGER DEFAULT 1,        -- 是否为最新版
    version     INTEGER DEFAULT 1,        -- 版本号
    is_static   INTEGER DEFAULT 0,        -- 长期 vs 短期
    is_forgotten INTEGER DEFAULT 0,
    forget_after TEXT,                    -- ISO datetime
    parent_memory_id TEXT,                -- 被此版本取代的旧版
    root_memory_id TEXT,                  -- 版本链根
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
```

- 新增 `memory_relations` 表:

```sql
CREATE TABLE memory_relations (
    source_id TEXT NOT NULL,              -- 源记忆
    target_id TEXT NOT NULL,              -- 目标记忆
    relation  TEXT NOT NULL               -- 'updates' | 'extends' | 'derives'
);
```

- 新增 `MemoryEntry` model + Manager 方法
- 集成到现有 `MemoryManager.search()` — 查询时只返回 `is_latest=1` 的版本

**收益:** Agent 能知道"用户之前喜欢 X，后来改主意了"，对话可追溯事实演变。

---

#### 2. 中间件自动注入

当前: Agent 必须显式调用 `memory_search` tool 来检索记忆。
目标: 每次 LLM 调用前自动注入相关记忆到 context。

**设计方案:**
- 在 orchestration 层加一个 `MemoryMiddleware`:

```python
class MemoryMiddleware:
    """自动在 LLM 调用前后处理记忆"""
    
    async def before_llm_call(self, context, user_input: str):
        """调用 LLM 前: 检索相关记忆 + profile, 注入到 system prompt"""
        memories = await self.memory_system.retrieve_context(user_input)
        profile = await self.memory_system.get_profile()
        context.inject_system_prompt(
            f"## 相关记忆\n{memories}\n## 用户画像\n{profile}"
        )
    
    async def after_llm_call(self, context, user_input: str, response: str):
        """调用 LLM 后: 保存这轮对话到记忆"""
        turn = MemoryTurn(user_input=user_input, agent_response=response)
        await self.memory_system.store_turn(turn)
```

- 这可以在 Anima 的 orchestration 层作为 LangGraph 节点或事件钩子接入

**收益:** Agent 不需要自己操心记忆，自然就"记住了"。

---

### P1 — 高价值，低实现成本

#### 3. User Profile (static + dynamic)

在现有 WikiManager 上加两个字段:

```python
class UserProfile:
    static: List[str]   # 长期稳定事实: ["喜欢 TypeScript", "用 Vim"]
    dynamic: List[str]  # 当前上下文: ["在调试 API 限流"]
```

- static 从 wiki/entities/ 和 wiki/concepts/ 自动提炼
- dynamic 从当前 ShortTermMemory 的最近 N 轮构建
- 每次 `retrieve_context()` 时一并返回

**收益:** Agent 立刻知道"在和谁说话"，个性化响应.

#### 4. 记忆关系标注

在现有 SQLite 基础上加 `memory_relations` 表。不需要改存储层，只需要:
- 新增一个表
- Ingest 时让 LLM 判断新事实和已有事实的关系 (updates/extends/derives)
- 搜索时可以利用关系做关联扩展

**收益:** Agent 可以回答"你上次说喜欢 X，后来是不是改主意了？"

---

### P2 — 低成本快速获胜

#### 5. Per-turn 缓存

在 `MemorySystem` 上加一个 `TurnCache`:

```python
class TurnCache:
    def __init__(self):
        self._cache: dict[str, str] = {}
    
    def make_key(self, session_id: str, user_input: str) -> str:
        return f"{session_id}:{hashlib.sha256(user_input.encode()).hexdigest()}"
    
    def get_or_compute(self, key: str, compute_fn):
        if key not in self._cache:
            self._cache[key] = compute_fn()
        return self._cache[key]
    
    def next_turn(self):
        self._cache.clear()  # 新轮次清空
```

**收益:** 同轮 Agent tool call 循环中，记忆检索只做一次。

---

## 五、技术实现建议

### 存储层

当前: SQLite + Chroma 并行。建议保持这个架构，新增 `memory_entries` 和 `memory_relations` 表即可。Chroma 不变。

### 架构整合

```
                    MemorySystem (统一入口)
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
     ShortTermMemory  MemoryManager  WikiManager
     (FIFO deque)     │              (Karpathy wiki)
                      │
           ┌──────────┴──────────┐
           ▼                     ▼
     SQLite FTS5             ChromaDB
     + memory_entries        (向量检索)
     + memory_relations
     + chunks / files
```

### 外部借鉴

Supermemory 的 `memory-graph` 包是 MIT 开源的，可以直接作为 Anima 的记忆可视化 UI 集成。Canvas 力导向图渲染器，显示六边形(记忆)+方块(文档)+三种关系边。

---

## 六、总结

Anima 的记忆系统已经有了很好的**存储基础设施**——SQLite + Chroma + Wiki 架构。Supermemory 真正值得借鉴的不是存储层，而是**记忆的智能处理层**:

1. **事实粒度** — 存原子事实，不是整段文本
2. **版本链** — 事实可追溯演变，矛盾自然解决
3. **主动注入** — 不需要 Agent 显式检索，自动给上下文
4. **用户画像** — 知道在和谁说话
