## Why

梗采集全链路已跑通（`ingested N`），但前端始终显示 0 条待筛选梗。根因是 `MemePool.add_from_candidate()` → `MemeStore.save()` → `WikiManager.write_page()` 持久化后，`list_active()` 查询返回空或 memes 的 `review_status` 不是 `"pending"`，导致 `on_meme_list` 过滤后无结果。

## What Changes

- `MemePool.add_from_candidate()` 和 `analyze_and_ingest()` 增加 INFO 日志，输出 meme id + review_status + 入库确认
- `MemeStore.get_active()` 增加 DEBUG 日志，输出 wiki 读到多少页、多少 active
- 检查 wiki 写入路径是否有静默失败（`write_page` 返回值不使用）
- 必要时强制 `MemeStore` 在 `save` 后 sync wiki index

## Capabilities

### Modified Capabilities
- `meme-review-api`: `on_meme_list` 和 `on_meme_collect` 返回的 pending 数现在与实际持久化的 meme 一致

## Impact

- **代码**: `memory/meme/engine.py`、`memory/meme/store.py`（日志 + 可能的 wiki sync 调用）
- **API**: 无 breaking change
