## 1. Heuristic 识别改进

- [x] 1.1 改进 `bilibili_collector.py` 的 `_heuristic_identify`：从标题中提取 2-4 字短语（排除停用词），从高赞评论中提取高频 n-gram
- [x] 1.2 添加 `_extract_title_phrases` 和 `_extract_comment_ngrams` 辅助方法
- [x] 1.3 验证：无 LLM 时 heuristic 也能产生至少几个梗候选

## 2. 采集结果反馈

- [x] 2.1 `PeriodicLearner.collect_bilibili_memes()` 改为返回 `int`（成功采集到 MemePool 的数量）
- [x] 2.2 `admin_handlers.py` 的 `on_meme_collect` 中，用实际采集数替代硬编码 `count=0`
- [x] 2.3 采集完成时日志输出明确结果（多少候选、多少成功采集）

## 3. 验证

- [x] 3.1 运行 `pytest tests/services/meme/` 确认已有测试通过
- [x] 3.2 触发采集并检查前端收到正确 `count`
