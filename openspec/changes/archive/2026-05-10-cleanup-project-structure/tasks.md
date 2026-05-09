## 1. 删除旧文件

- [x] 1.1 删除 `frontend-legacy/`（619MB 旧前端）
- [x] 1.2 删除 `assets/demo/`
- [x] 1.3 删除 `docs/ORAL_MEMORY_WORKER.md`
- [x] 1.4 删除 `MEMORY.md`
- [x] 1.5 删除废弃 spec（memory-relations, memory-versioning, pipeline-stats, socket-composable, supermemory-comparison-report）

## 2. 规范化文件结构

- [x] 2.1 创建 `docs/development/` 目录
- [x] 2.2 移动 `docs/deployment.md` → `docs/development/`
- [x] 2.3 移动 `docs/gpt-sovits-rtx5090-setup.md` → `docs/development/`
- [x] 2.4 `.env*` 保留在根目录（scripts/benchmark.py 等引用根路径 .env）
- [x] 2.5 删除空目录（frontend/resources/, frontend-legacy/resources/）
- [x] 2.6 清理 `.gstack/qa-reports/`

## 3. 验证

- [x] 3.1 更新 CLAUDE.md 中的 frontend-legacy/MEMORY.md 引用
- [x] 3.2 `.env` 保留根目录（脚本依赖）
- [x] 3.3 后端 17 测试通过
