## Context

热梗采集全链路：BilibiliMemeCollector.collect() → MemeCognitiveAnalyzer.analyze_and_ingest() → MemePool.add_from_candidate()。
断点在第一步：无 LLM 时 `_heuristic_identify` 几乎不产生候选。

## Goals / Non-Goals

**Goals:**
- 无 LLM 时也能产生合理梗候选
- 采集结果反馈给调用者
- 前端能看到实际采集数

**Non-Goals:**
- 不改变 MemePool/MemeCognitiveAnalyzer 的内部逻辑
- 不引入新依赖

## Decisions

### 1. Heuristic 改进：标题短语 + 评论热词

**选择**：从视频标题中切分有意义的 2-4 字短语，从高赞评论中提取高频 n-gram。

**理由**：标题和评论包含大量重复的句式/梗（如"绷不住了"、"难绷"、"这很XX"），适合启发式发现。

### 2. PeriodLearner.collect_bilibili_memes 返回 int

**选择**：方法签名改为返回 `int`（成功采集数），而非 `None`。

**理由**：调用方需要知道采集了多少梗来更新前端。

### 3. 前端反馈使用实际采集数

**选择**：handler 的 `on_meme_collect` 不再硬编码 `count=0`，而是用 `collect_bilibili_memes()` 返回值。

**理由**：用户需要看到"采集到 5 个新梗"而非"count=0"。

## Risks / Trade-offs

- **[风险] Heuristic 可能产生误报** → 保持 `persona_fit_score=0.5` 作为默认过滤阈值，用户筛选环节兜底
- **[风险] 评论 n-gram 计算开销** → 限制只处理 top 10 评论，提取 top 5 短语
