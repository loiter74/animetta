## Why

前端记忆相关 UI 有碎片化问题：`MemoryPanel`（wiki 浏览）和 `MemePanel`（梗管理）是两个独立 tab，`MemoryDrillDown` 是已废弃的 fuzzy drill-down 组件。记忆架构重构后（Wiki 统一存储），后端已统一，前端应该跟上。

## What Changes

- 删除 `MemoryDrillDown.vue`（已无用，引用已删除的 fuzzy 模块）
- 删除独立 Meme 组件（`MemePanel.vue` / `MemeAddForm.vue` / `MemeHistory.vue` / `meme.ts` store）
- 在 `MemoryPanel.vue` 中加入梗的增删功能（复用现有 `meme_add` / `meme_delete` 事件）
- `InteractivePanel.vue` 移除独立 `meme` tab，只保留统一 `memory` tab
- 统一记忆浏览面板：wiki 页面列表 + 快速添加梗 + 筛选

## Capabilities

### New Capabilities
*(None — UI cleanup only)*

### Modified Capabilities
*(None — no spec-level requirement changes)*

## Impact

- `frontend/src/components/memory/MemoryDrillDown.vue` → 删除
- `frontend/src/components/meme/` → 删除整个目录
- `frontend/src/stores/meme.ts` → 删除
- `frontend/src/components/memory/MemoryPanel.vue` → 加梗操作入口
- `frontend/src/components/layout/InteractivePanel.vue` → 去掉 meme tab
