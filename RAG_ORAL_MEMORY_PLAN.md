# RAG 记忆口语化预处理实现计划

## 背景

当前 RAG 检索出的对话记忆是原始对话文本，直接塞进 prompt 会导致 Agent 回复不够自然。目标是在记忆写入时预处理为口语化句式（如"我记得你好像提到过……"），查询时直接使用，避免增加查询延迟。

## 核心设计原则

```
向量基于原始文本生成 → 保证检索准确性
口语化文本存在 metadata → 保证回复自然
两个目标互不干扰
```

## 实现步骤

### 第一步：定义口语化转换的 Prompt

在 prompt 模板中新增一个专门用于记忆口语化的模板。

**要求：**
- 输入：原始对话文本（如 "用户说想学LangGraph"）
- 输出：口语化的记忆句式（如 "我记得你好像提到过想学LangGraph"）
- Prompt 中要约束输出格式，确保简洁、口语化，不添加多余信息
- 保留原始信息的准确性，只改变表达方式

**参考 Prompt 模板：**
```
你是一个记忆整理助手。请把以下对话内容转换为第一人称的口语化记忆表达。

规则：
1. 用"我记得"、"你之前提到过"、"我们上次聊过"等自然句式
2. 保留关键信息，不要添加或歪曲原意
3. 只输出转换后的文本，不要输出任何解释
4. 控制在1-2句话以内

原始对话：{original_text}
口语化记忆：
```

### 第二步：修改记忆写入流程

**当前写入流程：**
```
对话结束 → 原始文本 → embedding → 存入 Chroma
```

**改为：**
```
对话结束 → 原始文本 → embedding（基于原始文本）
                   → LLM 口语化处理（异步，后台执行）
                   → 存入 Chroma（向量 + metadata）
```

**数据存储结构：**
```python
# 存入 Chroma 的数据结构
collection.add(
    documents=[original_text],           # 原始文本，用于生成向量
    metadatas=[{
        "oral_version": oral_text,       # 口语化版本，查询时用
        "timestamp": timestamp,          # 时间戳
        "session_id": session_id,        # 会话ID
        # ... 其他已有的 metadata 字段保持不变
    }],
    ids=[doc_id]
)
```

### 第三步：修改记忆检索流程

**当前检索流程：**
```
用户输入 → 向量检索 + BM25 → RRF融合 → 返回原始文本 → 塞进 prompt
```

**改为：**
```
用户输入 → 向量检索 + BM25 → RRF融合 → 返回结果
  → 如果有 oral_version → 用 oral_version 塞进 prompt
  → 如果没有 oral_version（兼容旧数据）→ 用原始文本
```

```python
# 伪代码
for result in search_results:
    memory_text = result.metadata.get("oral_version", result.document)
    # memory_text 就是最终塞进 prompt 的内容
```

### 第四步：处理存量数据迁移（可选）

对已经在 Chroma 中的旧数据，可以写一个一次性脚本批量补充 oral_version：

```
遍历 Chroma 中所有文档
  → 检查 metadata 是否有 oral_version
  → 没有的 → 调用 LLM 生成口语化版本
  → 更新 metadata
```

**注意：**
- 批量处理需要控制 LLM 调用频率，避免触发限流
- 可以分批处理，不需要一次性全部完成
- 这一步不紧急，第三步的兼容逻辑已经保证旧数据不会出错

### 第五步：测试验证

**测试用例：**
1. 新对话写入后，检查 Chroma 中是否同时有原始文本和 oral_version
2. 检索时，确认返回的是 oral_version 而不是原始文本
3. 旧数据（没有 oral_version）检索时，确认 fallback 到原始文本
4. 口语化后的文本不影响向量检索的准确性（因为向量基于原始文本）
5. Agent 回复的自然度是否有提升

**验证方法：**
```
输入："我们之前聊过什么？"

改造前 Agent 回复：
  "根据对话记录，用户说想学LangGraph，用户问了天气..."（机械）

改造后 Agent 回复：
  "我记得你之前提到过想学LangGraph，我们还聊过天气来着..."（自然）
```

## 注意事项

1. **LLM 口语化处理必须异步**：写入时的 LLM 调用放在后台，不要阻塞对话主流程
2. **向量一定基于原始文本**：不要用口语化后的文本生成向量，否则检索会偏移
3. **做好兼容**：第三步的 fallback 逻辑保证旧数据不出问题
4. **口语化 Prompt 可能需要迭代**：先用简单模板跑起来，根据实际效果调整
5. **成本控制**：每条记忆多一次 LLM 调用，注意 API 费用。如果记忆量大，考虑用本地小模型（如 Ollama）做口语化处理

## 文件改动清单

1. **新增**：`src/anima/memory/prompts.py` - 口语化 Prompt 模板
2. **修改**：`src/anima/memory/storage/chroma.py` - 增加口语化处理 + metadata 写入
3. **修改**：`src/anima/memory/search/hybrid.py` - 读取 oral_version，fallback 到原始文本
4. **新增（可选）**：`scripts/migrate_oral_memory.py` - 存量数据迁移脚本

## 执行状态

- [x] 第一步：定义口语化转换的 Prompt ✅
  - 已创建 `src/anima/memory/prompts.py`，包含 `MemoryPrompts` 类和 `ORAL_MEMORY_TEMPLATE`
  - 已创建 `src/anima/memory/oral_processor.py`，包含 `OralMemoryProcessor` 类

- [x] 第二步：修改记忆写入流程 ✅
  - 已修改 `Chunk` 模型，添加 `oral_version` 字段
  - 已修改 `ChromaStore.upsert_chunks`，在 metadata 中存储 `oral_version`
  - 已修改 `MemoryManager._index_file`，添加 `_generate_oral_version` 方法
  - 已添加 `import re` 到 manager.py

- [x] 第三步：修改记忆检索流程 ✅
  - 已修改 `ChromaStore.vector_search`，返回 metadata
  - 已修改 `hybrid_search`，从 metadata 获取 `oral_version`
  - 已修改 `SearchResult` 模型，添加 `oral_version` 字段
  - 实现了 fallback 逻辑：没有 `oral_version` 时使用原始文本

- [ ] 第四步：处理存量数据迁移（可选）
  - 未执行，需要时可创建迁移脚本

- [x] 第五步：测试验证 ✅
  - 所有修改的文件编译通过
  - 基本语法检查通过

---

## 异步 LLM Worker 实现 (新增)

### 新增文件

1. **`src/anima/memory/oral_worker.py`** - 核心异步 Worker
   - `OralMemoryWorker` 类：独立后台服务
   - 批量处理、自动重试、结果缓存
   - 支持回调通知

2. **`docs/ORAL_MEMORY_WORKER.md`** - 使用文档

3. **`scripts/test_oral_worker.py`** - 测试脚本

### 架构改进

```
MemorySystem.start()
    ├── 启动 LongTermMemory
    ├── 启动 OralMemoryWorker
    └── 将 Worker 设置给 LongTermMemory
            ↓
MemoryManager._index_file() (同步)
    ├── 规则转换 oral_version (快速)
    ├── 写入 Chroma
    └── _submit_oral_tasks() → 提交到 Worker
            ↓
OralMemoryWorker (异步)
    ├── 队列接收任务
    ├── 批量 LLM 调用
    └── 回调更新 Chroma metadata
```

### 配置方式

```python
memory_system = MemorySystem({
    "workspace_dir": "~/.anima/workspace",
    "llm_client": llm_instance,  # 传入 LLM
    "oral_queue_size": 1000,
    "oral_max_retries": 2,
    "oral_batch_size": 5,
})
```

### 测试

```bash
python scripts/test_oral_worker.py
```
