## Context

Anima 已有完整的 MemePool 系统（`src/anima/memory/meme/`），管理 10 个活跃梗的生命周期（时间衰减打分、复活机制）。但当前 MemeDiscoverer 只能从内部对话模式中生成梗，无法感知 B 站等外部平台的流行文化。同时 Anima 已有 B 站直播弹幕接收能力（`src/anima/services/live/bilibili_danmaku.py`），但仅限于接收弹幕，不具备分析交互模式的能力。

本次设计在现有 MemePool + PeriodicLearner 架构上扩展，新增 B 站外部数据源和交互学习能力。

## Goals / Non-Goals

**Goals:**
- 定期从 B 站热门视频采集新兴梗，经 LLM 认知分析后流入 MemePool
- 升级 `select_for_context()` 从关键词匹配到语义匹配，让 AI 在对话中自然接梗
- 分析 B 站直播间的弹幕交互模式，生成可操作的直播优化策略
- 所有新功能通过 PeriodicLearner 定时调度，无需手动触发

**Non-Goals:**
- 不做实时弹幕分析（已有 danmaku 接收，本次只做离线模式学习）
- 不覆盖 B 站以外的平台（微博、Reddit 等）
- 不修改现有 MemePool 的生命周期逻辑（衰减、复活、评分保持不变）
- 不引入新的向量数据库或搜索引擎（复用现有 Chroma + SQLite FTS5）

## Decisions

### Decision 1: B 站采集使用 bilibili-api-python 的 `search` + `video` API

- **选择**：使用项目已有依赖 `bilibili-api-python` 的 `search.search_by_type()` 获取热门视频，`video.Video.get_info()` 获取详情，`comment.get_comments()` 抓取高赞评论
- **备选**：直接用 HTTP 请求 B 站 API（需要自行处理签名/wbi 鉴权，复杂度高）
- **理由**：项目已安装此依赖（`bilibili_danmaku.py` 使用），零额外成本

### Decision 2: 认知分析使用 LLM 结构化输出

- **选择**：构造专用 system prompt，要求 LLM 输出 JSON 格式的认知分析结果（幽默机制、使用场景、情感色彩、适配人设风格）
- **备选**：使用本地 NLP 模型做情感/语义分析（精度不足，无法理解梗的文化语境）
- **理由**：梗的认知分析本质上是语义理解和文化推理任务，LLM 是最适合的工具。每次调用约 1-2K tokens，成本可控

### Decision 3: 语义匹配复用现有 Hybrid Search

- **选择**：`select_for_context()` 改用 `memory/search/hybrid.py` 的混合搜索（70% 向量 + 30% BM25），将用户输入作为 query，在 MemePool 中检索最匹配的梗
- **备选**：继续用关键词匹配（精度太低）；用单独 embedding 模型（增加复杂度）
- **理由**：完全复用现有基础设施，且混合搜索已在 Anima 中验证效果良好

### Decision 4: 交互模式学习作为独立分析管道

- **选择**：`BilibiliInteractionLearner` 分析 B 站热门直播间弹幕的统计模式（回应频率分布、梗使用时机、情感流动曲线），输出 `InteractionPattern` 结构化数据存入 Wiki
- **理由**：与梗采集关注点不同——一个关注"内容"（什么梗），一个关注"形式"（怎么用）。两者解耦可独立迭代

### Decision 5: 调度通过 PeriodicLearner 扩展

- **选择**：在 `PeriodicLearner` 中新增两个调度任务：`collect_bilibili_memes()` 和 `learn_interaction_patterns()`
- **备选**：用独立的 APScheduler/Celery 任务（过度设计）
- **理由**：PeriodicLearner 已有 `AsyncScheduler` 基础设施，新增任务只需注册回调

## Data Model Changes

```python
@dataclass
class CognitiveAnalysis:
    """LLM 认知分析结果"""
    humor_mechanism: str          # "双关", "反讽", "荒诞", "自指", "谐音", "反差"
    context_trigger: str          # 触发场景描述
    emotional_tone: str           # "幽默", "讽刺", "自嘲", "温暖", "荒诞"
    persona_fit_score: float      # 0-1 与当前人设的匹配度
    usage_example: str            # 对话中使用示例
    source_url: str               # B 站视频链接

# Meme 模型新增字段
class Meme:
    ...
    cognitive_analysis: Optional[CognitiveAnalysis] = None  # 新增
    source_platform: str = "internal"  # "internal" | "bilibili" | "user"
```

## Risks / Trade-offs

- **[Risk] B 站 API 限流或反爬** → 设置合理请求间隔（>1s），缓存热门视频列表减少重复请求，错误时降级为使用已缓存的梗数据
- **[Risk] LLM 分析质量不稳定** → 使用结构化 JSON 输出 + schema 校验，分析失败时降级为仅有基础字段（text + context_hint）的裸梗
- **[Risk] 语义匹配可能误匹配不合适的梗** → 设置 `persona_fit_score` 阈值（默认 0.5），低于阈值的不注入
- **[Risk] 交互模式学习需要大量数据才有统计意义** → 首次运行收集足够样本（至少 100 条弹幕交互），不足时跳过分析并记录日志
