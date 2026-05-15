## Context

`analyze_and_ingest` → `add_from_candidate` → `store.save()` → `wiki.write_page()` 链路写入 wiki。`list_active()` → `get_active()` → `wiki.list_pages()` 读 wiki。`ingested 3` 但 `pending 0` 说明写入和读取之间存在断层。

## Goals / Non-Goals

**Goals:**
- 定位「写入成功但查询不到」的根因
- 确保 `add_from_candidate` 后 memes 能被 `list_active()` 立刻查询到

**Non-Goals:**
- 不改动 wiki 架构本身

## Decisions

### Decision: 两阶段修复——先诊断再修复

**Phase 1 诊断**: 在关键路径加日志，重启后采集一次，从日志确认断点：
- `add_from_candidate`: 输出 meme id + 是否保存成功
- `get_active`: 输出 wiki 读到的总页数 + active 数
- `on_meme_collect`: 输出 `list_active()` 返回的原始数量

**Phase 2 修复**: 根据诊断结果选择方案：
- 若 wiki 写入失败 → 检查 `write_page` 返回值/异常
- 若 wiki 读取不到 → 在 `save()` 后调用 `wiki.rebuild_index()` 强制刷新
- 若 `review_status` 错误 → 修复序列化/反序列化

## Risks

- **[Risk] 可能需改动 wiki 核心逻辑** → 先诊断再改，最小化影响面
