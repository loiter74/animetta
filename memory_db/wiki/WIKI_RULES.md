# LLM Wiki 管理规约 (Karpathy-style, VTuber Adapted)

> 本文件定义了 AI 维护的 Wiki 知识库的管理规则，所有 INGEST / QUERY / LINT 操作必须遵守。

---

## 1. 目录结构

```
memory_db/
├── raw/                     # 不可变的原始对话日志
│   └── YYYY-MM-DD.md
├── wiki/                    # AI 维护的知识库
│   ├── index.md             # 主目录 (自动生成，禁止手动编辑)
│   ├── log.md               # 操作日志 (append-only)
│   ├── WIKI_RULES.md        # 本文件 - 管理规约
│   ├── entities/            # 实体页: 人物、角色、宠物、项目
│   │   └── name.md          # 包含提及记录 + [[双链]]
│   ├── concepts/            # 概念页: 偏好、兴趣、习惯、模式
│   │   └── type-name.md     # 包含相关对话引用
│   ├── sources/             # 每日对话摘要
│   │   └── YYYY-MM-DD.md    # 链接回 raw/ 原始日志
│   └── synthesis/           # 跨源分析 (合成页)
│       └── topic.md         # 跨时间线的主题综合
├── memory.sqlite            # SQLite FTS5 + 元数据索引
└── chroma_db/               # 向量嵌入 (语义搜索)
```

---

## 2. 三大工作流

### 2.1 INGEST (对话 → 知识)

每条对话轮次经过:

1. **raw 写入** - 追加到 `raw/YYYY-MM-DD.md`，不可变
2. **评分** - MemoryScorer 打分 (0~1)
3. **提取** - 通过正则规则提取实体和概念
4. **页面更新** - 创建/追加到 entities/ 或 concepts/ 页面
5. **摘要更新** - 更新当天的 sources/ 页面
6. **索引重建** - 更新 wiki/index.md
7. **日志记录** - 追加到 wiki/log.md

**跳过条件**: score < 0.3 的低重要性轮次不处理

### 2.2 QUERY (知识 → 上下文)

为 LLM system prompt 提供记忆上下文:

1. 加载今天 + 昨天的 sources/ 摘要
2. 对查询执行混合搜索 (向量语义 + BM25 关键词)
3. 格式化为 MemoryTurn 对象返回

### 2.3 LINT (健康检查)

定期检查 wiki 健康:

- 断链检测: `[[xxx]]` 指向不存在的页面
- 孤立页面: 没有任何双链指向的页面
- 索引漂移: index.md 与实际页面不一致
- 不自动修复，仅报告

---

## 3. 页面格式

每个 wiki 页面使用 **YAML frontmatter + Markdown**:

```markdown
---
title: 页面标题
type: entity | concept | source | synthesis
tags: [tag1, tag2]
created: YYYY-MM-DDTHH:MM:SS
updated: YYYY-MM-DDTHH:MM:SS
links: [[other-page]]
---

# 页面标题

正文内容，支持 [[双链]] 引用其他页面。
```

### 双链规则

- 使用 `[[page-name]]` 格式引用其他页面
- 被引用页面应出现在 links 列表中
- LINT 检查所有双链的有效性

---

## 4. VTuber 专用提取规则

### 4.1 实体提取 (entities/)

| 类型 | 匹配模式 | 示例 |
|------|----------|------|
| name | `我叫X`, `我的名字是X`, `叫我X` | "我叫小明" → entities/小明.md |
| age | `我今年X岁`, `我X岁` | "我25岁" → 写入实体页 |
| pet | `养了一只猫叫X`, `有只狗叫X` | "养了一只猫叫团子" → entities/团子.md |
| location | `我住在X`, `我在X上班` | "我在北京工作" → 写入实体页 |

### 4.2 概念提取 (concepts/)

| 类型 | 匹配模式 | 示例 |
|------|----------|------|
| like | `我喜欢X`, `X是我的最爱` | "我喜欢打游戏" → concepts/like-打游戏.md |
| dislike | `我讨厌X`, `我不喜欢X` | "我最讨厌加班" → concepts/dislike-加班.md |
| want | `我想X`, `我打算X` | "我想学画画" → concepts/want-学画画.md |

### 4.3 重要标记 (强制高评分)

以下模式强制将重要性评分提升至 >= 0.6:

- `记住X`
- `别忘了X`
- `重要的是X`
- `记录X` / `记一下X` / `写下来X`

---

## 5. 自动整理规则 (Organizer)

### 触发方式

通过前端 "记忆整理" 按钮手动触发。

### 整理流程

1. **收集** - 读取所有 entities/ + concepts/ + sources/ 页面
2. **分析** - 构建关系图 (双链 + 共现 + 标签)
3. **聚类** - 使用 LLM 识别主题聚类
4. **合并** - 合并重复/相似页面
5. **合成** - 创建 synthesis/ 页面总结长期主题
6. **重建** - 重建 index.md + 搜索索引

### 整理原则

- **不删除 raw/** - 原始日志永远不可变
- **不丢失信息** - 合并页面保留所有提及记录
- **保持简洁** - 每个主题一页，避免碎片化
- **双链完整** - 更新所有受影响的双链引用

---

## 6. 命名规范

- 文件名: 使用拼音或英文，`-` 分隔，最多 60 字符
- 页面标题: 保持原始名称 (中文/日文均可)
- Tags: 使用小写英文或日期 (YYYY-MM-DD)
- 路径: `entities/`, `concepts/`, `sources/`, `synthesis/` 四个子目录

---

## 7. 不可变规则

1. `raw/` 目录下的文件**绝不修改**，只追加
2. `index.md` 由系统自动生成，**禁止手动编辑**
3. `log.md` 只追加，**不删除历史条目**
4. 每次页面修改都记录到 `log.md`
5. 页面更新时保留 `created_at`，只更新 `updated_at`
