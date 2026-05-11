## Why

Anima 现有的 Wiki Memory 架构具备对话存储、混合搜索、层级组织，但缺少**自动从对话中提取结构化事实**的能力。当前事实需人工写入 Wiki Markdown 文件，无法自动学习用户偏好或对话中产生的新信息。从认知科学视角，这相当于缺少"从情景记忆（对话日志）到语义记忆（Wiki 知识库）的巩固过程"。

## What Changes

- 在 `PeriodicLearner` 或新的定时任务中，增加 LLM 调用：从最近 N 轮对话日志中提取结构化事实
- 提取的事实用 Pydantic schema（事实类型、置信度、来源追溯）存储
- 写入 Wiki Memory（Markdown 文件），与现有人工编写的知识共存
- 支持去重和更新——同主题新事实更新旧条目，避免冗余

## Capabilities

### New Capabilities
- `auto-fact-extraction`: LLM 自动从对话日志提取结构化事实，写入 Wiki Memory。关键行为：定时触发（非实时）、可追溯来源、支持去重更新。

## Impact

- `src/anima/memory/learner/`: 新增 fact extraction 模块
- `src/anima/memory/wiki/`: 可能需要支持自动写入的目录隔离
- 新增一次 LLM 调用（定时，非实时），不影响对话延迟
