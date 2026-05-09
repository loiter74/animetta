## Context

后端记忆架构已统一为 Wiki 唯一存储（`page_type="meme"` 的梗已作为 wiki 页面存在），但前端 UI 还是分开的两套：
- `MemoryPanel` — wiki 页面浏览（entities/concepts/synthesis/source/meme）
- `MemePanel` + `MemeAddForm` + `MemeHistory` — 独立梗管理

`MemoryDrillDown` 引用已删除的 FuzzyMemory 模块，纯死代码。

## Goals / Non-Goals

**Goals:**
- 删除死代码 `MemoryDrillDown.vue`
- 删除独立 meme 组件目录（`MemePanel/MemeAddForm/MemeHistory/meme.ts`）
- 在 wiki 浏览面板底部加快速添加梗入口
- `InteractivePanel` 只保留一个统一 `memory` tab

**Non-Goals:**
- 不改变后端 meme_add/meme_rate/meme_delete 事件（它们仍有效）
- 不改变 MemePool 或 wiki 存储逻辑

## Decisions

1. **MemeAddForm 内联到 MemoryPanel 底部** — 简单输入框 + 发送按钮，复用 `meme_add` socket 事件。不保留 MemeHistory（梗历史在 wiki 浏览面板的 meme 筛选下可见）。
2. **删除 MemeHistory** — wiki 浏览面板已支持按 `page_type="meme"` 筛选，取代了独立历史列表。
3. **去掉独立 meme tab** — `InteractivePanel` 不再需要 `meme` 标签。用户点击 "📖 记忆浏览" 即可看到全部内容（含梗）。

## Risks / Trade-offs

- **[Low] 用户失去独立梗评分功能** — MemePanel 有 meme_rate 按钮，删除后梗评分只能通过后端自动调度（maintain_meme_pool）。可接受，因为评分衰减是自动的。
