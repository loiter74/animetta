## Why

Anima 的 MemePool（梗记忆池）目前只能从内部对话模式中生成梗，无法感知外部互联网流行文化。B 站作为中文互联网梗文化的核心发源地，其热门视频、评论区互动模式和弹幕文化是 AI VTuber 理解并自然使用梗的关键数据源。同时，学习 B 站直播间的交流互动模式可以让 Anima 的直播表现更贴近真人主播。

## What Changes

- **新增 B 站热梗采集服务**：定期从 B 站热门视频采集标题、标签、高赞评论，识别新兴梗
- **新增梗认知分析管道**：用 LLM 分析梗的幽默机制（双关/反讽/荒诞等）、使用场景、情感色彩，生成结构化认知描述
- **增强 MemePool 数据模型**：Meme 模型增加 `cognitive_analysis` 字段存储认知分析结果
- **增强上下文匹配**：`select_for_context()` 从关键词匹配升级为语义匹配，让 AI 在对话中更自然地接梗
- **新增 B 站交互模式学习**：分析 B 站直播间的弹幕互动模式（回应节奏、梗使用时机、观众情绪响应），生成直播优化策略
- **集成 PeriodicLearner 调度**：在现有定时学习管道中加入 B 站采集和分析任务

## Capabilities

### New Capabilities
- `bilibili-meme-collector`: B 站热梗视频采集与评论抓取，识别新兴梗并提取关键上下文
- `meme-cognitive-analysis`: LLM 驱动的梗认知分析，输出幽默机制、使用场景、情感色彩等结构化描述
- `bilibili-interaction-learning`: B 站直播间交互模式学习，分析弹幕互动规律生成直播优化策略
- `meme-context-injection`: 对话中基于语义匹配的梗上下文注入，让 AI 自然接梗

### Modified Capabilities
<!-- No existing specs have requirement-level changes -->

## Impact

- **新增文件**: `src/anima/services/meme/bilibili_collector.py`, `src/anima/services/meme/bilibili_interaction.py`, `src/anima/services/meme/analyzer.py`
- **修改文件**: `src/anima/memory/meme/models.py` (增加 cognitive_analysis 字段), `src/anima/memory/meme/engine.py` (语义匹配升级), `src/anima/memory/learner/engine.py` (调度集成)
- **依赖**: 复用现有 `bilibili-api-python` 依赖，无需新增外部库
- **LLM 成本**: 每次分析调用约 1-2K tokens，建议每天执行 1-2 次
