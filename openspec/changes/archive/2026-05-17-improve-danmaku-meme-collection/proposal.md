## Why

弹幕热梗采集功能目前每次只能采集到 2-3 条意义不大的数据。核心原因是数据源仅依赖 B站热门视频榜单（hot.get_hot_videos），而梗的真正发酵地在实时弹幕流中。同时项目已有 `BilibiliDanmakuService`（实时弹幕接收能力）和 `BilibiliInteractionLearner`（弹幕交互分析），但这两者与采集管道完全隔离。需要打通弹幕流、优化采集策略来提升数据质量与数量。

## What Changes

- **打通弹幕数据源**：新增 `DanmakuBuffer` 组件连接 `BilibiliDanmakuService`，实时累积弹幕并提供高频短语统计；`BilibiliMemeCollector` 新增弹幕数据源，LLM prompt 增加弹幕分析维度
- **采集并行化**：视频评论获取从串行（for + 1s delay）改为 `asyncio.gather` 并行
- **参数调优**：`max_videos: 20→50`, `max_comments: 20→50`, `request_delay: 1.0→0.3`, 超时 60→120s
- **LLM Prompt 升级**：增加跨视频交叉验证、弹幕高频模式识别
- **Heuristic 升级**：字符 2-gram → jieba 分词 + 语义 n-gram + TF-IDF 过滤
- **MemeDiscoverer 候选扩容**：`meme_candidates_per_run: 3→15`
- **MemePool 槽位扩容**：`max_active: 10→20`

## Capabilities

### New Capabilities
- `danmaku-buffer`: 实时弹幕缓冲区组件。从 `BilibiliDanmakuService` 接收弹幕，按时间窗口统计高频短语，为采集管道提供弹幕数据源

### Modified Capabilities
- `bilibili-meme-collector`: 采集器需求变更——新增弹幕数据源（实时弹幕 + 历史弹幕）、评论获取并行化、LLM prompt 增加弹幕模式识别维度、Heuristic 升级为语义级短语提取

## Impact

- `src/anima/services/meme/bilibili_collector.py` — 采集器核心改造：新数据源、并行化、新 prompt、新 heuristic
- `src/anima/services/meme/bilibili_interaction.py` — 增加弹幕高频短语输出
- `src/anima/services/meme/` — 新增 `danmaku_buffer.py` 文件
- `src/anima/services/live/bilibili_danmaku.py` — 需要暴露弹幕接口给 DanmakuBuffer
- `src/anima/memory/meme/engine.py` — MemePool max_active 配置变更
- `src/anima/memory/learner/meme_discovery.py` — 候选数扩容
- `config/features/memory.yaml` — MemePool 配置参数变更
