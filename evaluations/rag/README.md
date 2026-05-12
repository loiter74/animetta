# RAG Evaluation Dataset

## 数据来源

评估数据集基于 Anima 的 Wiki 记忆系统构建：

- **标注来源**：`memory_db/wiki/log.md`（130+ 条摄取操作记录，包含每次 fact 提取的来源文件）
- **语料库**：`memory_db/wiki/` 和 `memory_db/raw/` 下的 45 个 Markdown 文件
- **主要用户**：小明（2026-04-08 起），辅助：遗留数据（Alice、小红、张伟）

## 标注规则

### 数据格式

每行一条 JSON：

```json
{
  "id": "q001",
  "query": "我的猫叫什么名字？",
  "expected_chunks": [
    {"path": "wiki/entities/团子.md", "start_line": 1, "end_line": 5}
  ],
  "expected_docs": ["wiki/entities/团子.md"],
  "category": "factual",
  "difficulty": "easy",
  "notes": "单文档单chunk定位"
}
```

### 类别定义

| 类别 | 说明 | 最少条数 |
|------|------|---------|
| factual | 单跳事实查询，可直接从单个 chunk 回答 | 10 |
| contextual | 需要上下文理解的查询（"刚才说的那个..."） | 10 |
| temporal | 时间相关查询（"上周..."、"从3月到现在..."） | 10 |
| persona | 人设/偏好相关查询（"Aura的金句"） | 10 |
| multi_hop | 需综合多个文档的查询 | 10 |
| robustness | 含拼写错误或口语化表达 | 5 |

### Difficulty 标注

- `easy`：单文档单 chunk 可直接回答
- `medium`：需要多个 chunk 或简单推理
- `hard`：跨文档综合或需要时间推理

### Chunk 定位

Chunk 通过 `(path, start_line, end_line)` 三元组定位，与 `SearchResult` 的字段一致。`start_line` 和 `end_line` 是源文件中的行号（1-based）。

## 验证

```bash
# 检查 JSONL 格式
jq . evaluations/rag/dataset.jsonl | head -5

# 统计类别分布
jq -r '.category' evaluations/rag/dataset.jsonl | sort | uniq -c

# 检查总条数
wc -l evaluations/rag/dataset.jsonl
```
