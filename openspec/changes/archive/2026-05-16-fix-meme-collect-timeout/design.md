## Context

`BilibiliMemeCollector.collect()` 通过 `loop.run_in_executor()` 调用 B 站 API，无超时控制。20 个视频 × (评论 API + 1s delay) 约 40s，LLM 分析再加 30s，总计 ~70s。前端 `MemeReview.vue` 超时为 30s，远不够。

## Goals / Non-Goals

**Goals:**
- 后端 API 调用有超时保护，避免无限阻塞
- 超时后优雅降级：返回已采集数据而非全部丢弃
- 前端超时匹配实际耗时

**Non-Goals:**
- 不改变采集策略（仍按顺序抓评论）
- 不优化 LLM 调用并发（后续可单独做）

## Decisions

### Decision 1: 两层超时——整体 + 单次 API

**选择**: `collect()` 整体 60s 超时 + 每个评论 API 调用 10s 超时。

```python
# 整体超时
videos = await asyncio.wait_for(self._fetch_trending_videos(), timeout=15)
# 单次 API 超时
comments = await asyncio.wait_for(
    loop.run_in_executor(None, lambda: sync(comment_api_call)),
    timeout=10
)
```

**理由**: B 站 API 偶尔慢但不会完全挂。整体超时保底，单次超时防止个别视频拖垮整个采集。

### Decision 2: 前端超时 120s

**选择**: `MemeReview.vue` 将 `setTimeout(30000)` 改为 `setTimeout(120000)`。

**理由**: 120s 覆盖正常采集（~70s）+ 1 次重试的余量。用户等待 2 分钟可接受（采集非高频操作）。

### Decision 3: 超时后部分降级

**选择**: `asyncio.TimeoutError` 被捕获后，返回已成功采集的 videos/comments，而非空列表。

**理由**: 部分数据比零数据好。10 个视频的梗也比 0 个强。

## Risks / Trade-offs

- **[Risk] 120s 前端等待体验差** → 后续可改为异步采集（后台执行 + 完成后通知），本次不做
- **[Risk] B 站 API 限流** → 已有 1s delay，超时后不会加重请求频率
