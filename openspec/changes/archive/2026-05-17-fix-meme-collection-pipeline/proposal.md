## Why

B站热梗采集功能存在 3 个问题导致"不好用"：
1. 无 LLM 时启发式降级 `_heuristic_identify` 只匹配标签去重，热门视频标签几乎全唯一 → 永远返回空
2. `collect_bilibili_memes()` 不返回采集结果，handler 始终报 `count=0`
3. 所有异常被静默吞掉，用户不知道采集是否成功

## What Changes

- 改进 `_heuristic_identify`：从视频标题和高赞评论中提取有意义短语/双关语/句式
- `collect_bilibili_memes()` 返回成功采集数
- `on_meme_collect` handler 使用实际计数通知前端
- 采集结束时日志明确输出结果

## Capabilities

### New Capabilities
- `meme-collection-robustness`: 无 LLM 模式下的热梗启发式识别改进、采集结果反馈

### Modified Capabilities
<!-- None -->

## Impact

- `src/anima/services/meme/bilibili_collector.py`: 改进 `_heuristic_identify`
- `src/anima/memory/learner/engine.py`: `collect_bilibili_memes` 返回 int
- `src/anima/orchestration/server/handlers/admin_handlers.py`: 使用实际计数
