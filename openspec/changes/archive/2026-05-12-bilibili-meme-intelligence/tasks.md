## 1. 数据模型扩展

- [x] 1.1 在 `src/anima/memory/meme/models.py` 中新增 `CognitiveAnalysis` dataclass（humor_mechanism, context_trigger, emotional_tone, persona_fit_score, usage_example, source_url）
- [x] 1.2 在 `Meme` dataclass 中新增 `cognitive_analysis: Optional[CognitiveAnalysis]` 和 `source_platform: str` 字段，默认值 `source_platform="internal"`
- [x] 1.3 更新 `Meme.to_dict()` 序列化 cognitive_analysis 字段
- [x] 1.4 更新 `MemeStore._meme_to_page()` 和 `_page_to_meme()` 支持 cognitive_analysis 的持久化和反序列化

## 2. B 站热梗采集

- [x] 2.1 创建 `src/anima/services/meme/__init__.py` 包
- [x] 2.2 创建 `src/anima/services/meme/bilibili_collector.py`，实现 `BilibiliMemeCollector` 类
- [x] 2.3 实现热门视频采集：使用 `bilibili-api-python` search API 获取热门视频列表（title, tags, view_count, description）
- [x] 2.4 实现高赞评论抓取：对每个视频抓取前 20 条高赞评论（content, likes, replies, time）
- [x] 2.5 实现 LLM 驱动的梗候选识别：分析标题和高频评论，识别新兴梗模式
- [x] 2.6 添加 API 请求限流保护（1s 延迟）和错误降级（部分失败不阻塞整体）

## 3. 梗认知分析管道

- [x] 3.1 创建 `src/anima/services/meme/analyzer.py`，实现 `MemeCognitiveAnalyzer` 类
- [x] 3.2 设计认知分析 LLM prompt：要求输出 JSON 格式（humor_mechanism, context_trigger, emotional_tone, persona_fit_score, usage_example）
- [x] 3.3 实现 JSON schema 校验：必填字段缺失时标记分析失败
- [x] 3.4 实现分析失败降级：LLM 调用失败时创建仅有基础字段的 Meme
- [x] 3.5 实现 `MemeCandidate` → `CognitiveAnalysis` → `MemePool.add_from_candidate()` 的完整管道

## 4. B 站交互模式学习

- [x] 4.1 创建 `src/anima/services/meme/bilibili_interaction.py`，实现 `BilibiliInteractionLearner` 类
- [x] 4.2 实现弹幕数据采集：连接可配置的 B 站热门直播间，每个直播间采集至少 100 条弹幕
- [x] 4.3 实现 LLM 驱动的交互模式分析：回应频率分布、梗使用时机、情感流动曲线、互动类型分类
- [x] 4.4 定义 `InteractionPattern` 数据模型（模式名称、描述、适用场景、置信度）
- [x] 4.5 实现直播优化策略生成：基于交互模式输出具体的行为建议（触发条件、建议行为、预期效果、优先级）
- [x] 4.6 实现策略存储：写入 Wiki（`wiki/concepts/livestream-strategy.md`），支持 Hybrid Search 检索
- [x] 4.7 实现用户数据匿名化：不存储 UID 和个人信息

## 5. 语义匹配升级

- [x] 5.1 重写 `MemePool._context_match()` 为语义匹配，使用 `memory/search/hybrid.py` 的 Hybrid Search
- [x] 5.2 在 `select_for_context()` 中集成 cognitive_analysis 的 persona_fit_score 作为匹配阈值（默认 0.5）
- [x] 5.3 实现无合适梗时的优雅降级：返回 None，不注入上下文

## 6. 梗上下文注入

- [x] 6.1 在 `memory/middleware` 或 graph node 中实现 `[MemeContext]` 注入逻辑
- [x] 6.2 注入格式：梗文本 + context_hint + usage_example，标记为可选参考（不强制 LLM 使用）
- [x] 6.3 实现梗使用后评分更新：`MemePool.score_after_use(meme_id, effectiveness)`
- [x] 6.4 支持按 `source_platform` 过滤（如只使用 B 站来源的梗）

## 7. PeriodicLearner 调度集成

- [x] 7.1 在 `PeriodicLearner.__init__()` 中初始化 `BilibiliMemeCollector` 和 `BilibiliInteractionLearner`
- [x] 7.2 新增调度任务 `collect_bilibili_memes()`：每天执行 1-2 次
- [x] 7.3 新增调度任务 `learn_interaction_patterns()`：每次直播前执行
- [x] 7.4 实现任务失败不影响其他调度任务的隔离机制

## 8. 测试

- [x] 8.1 为 `BilibiliMemeCollector` 编写单元测试（mock B 站 API 响应）
- [x] 8.2 为 `MemeCognitiveAnalyzer` 编写单元测试（测试 JSON 解析和降级逻辑）
- [x] 8.3 为 `BilibiliInteractionLearner` 编写单元测试（mock 弹幕数据）
- [x] 8.4 为升级后的 `MemePool._context_match()` 编写语义匹配测试
- [x] 8.5 运行 `PYTHONPATH=src python -m pytest tests/ -v` 确保无回归
