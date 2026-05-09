## Why

项目累积了大量旧文件：619MB 的旧前端备份、已迁移功能的文档、废弃的 spec、散落在根目录的配置文件。同时文件结构不规范（文档、env 文件散落各处）。

## What Changes

### 删除
- `frontend-legacy/` — 旧前端备份（Vue3 迁移已完成）
- `assets/demo/` — 旧 demo gif
- `docs/ORAL_MEMORY_WORKER.md` — 已删除功能的文档
- `MEMORY.md` — 与 CLAUDE.md 重复
- `openspec/specs/memory-relations/`, `memory-versioning/`, `pipeline-stats/`, `socket-composable/`, `supermemory-comparison-report.md` — 已废弃 spec

### 移动
- `docs/deployment.md` → `docs/development/deployment.md`
- `docs/gpt-sovits-rtx5090-setup.md` → `docs/development/`
- `.env*` → `config/`（统一管理配置文件）

### 清理
- `frontend/resources/`, `frontend-legacy/resources/` — 空目录
- `.gstack/qa-reports/` — QA 截图缓存

## Impact

- 释放约 620MB 磁盘空间
- 配置文件统一到 `config/`
- 文档目录结构清晰化
