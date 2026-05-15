## Why

B 站梗采集耗时 ~70s（20 视频 × 评论抓取 + LLM 分析），远超前端 30s 超时，导致前端显示"采集超时"且后端采集被中断。后端 B 站 API 调用无超时保护，网络慢时线程永久阻塞。

## What Changes

- **后端**: `BilibiliMemeCollector._fetch_trending_videos()` 和 `collect()` 增加 `asyncio.wait_for()` 超时保护（默认 60s 可配置），超时后返回已采集的部分数据而非整体失败
- **前端**: `MemeReview.vue` 采集超时从 30s 延长到 120s，匹配实际采集耗时

## Capabilities

### Modified Capabilities
- `bilibili-meme-collector`: `_fetch_trending_videos()` 和 `collect()` 增加可配置超时，超时后降级返回部分结果
- `meme-review-ui`: 前端采集超时从 30s 延长到 120s

## Impact

- **代码**: `bilibili_collector.py`（2 处 asyncio.wait_for + 默认超时配置）、`MemeReview.vue`（1 处超时常量）
- **配置**: `config/features/memory.yaml` 可增加 `bilibili_meme.collector.request_timeout`（可选）
- **API**: 无 breaking change
