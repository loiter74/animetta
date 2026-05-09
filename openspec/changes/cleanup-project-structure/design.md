## Context

项目在多次架构迁移后（Vanilla JS → Vue3, EventBus → LangGraph, 多存储 → Wiki 统一）累积了大量遗留文件。

## Goals / Non-Goals

**Goals:**
- 删除 620MB 旧前端
- 删除废弃文档和 spec
- 统一 env 配置到 config/
- 规范化 docs/ 目录结构

**Non-Goals:**
- 不改代码逻辑
- 不删运行时数据（memory_db/, data/）
- 不删 ADR 文档（历史价值）
