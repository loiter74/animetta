## Context

### 当前状态

弹幕热梗采集管道目前只有一条数据源——B站热门视频榜单 + 视频评论：

```
用户点击"采集热梗"
  → on_meme_collect()
    → PeriodicLearner.collect_bilibili_memes()
      → BilibiliMemeCollector.collect()
        ├─ hot.get_hot_videos() → 20 videos (热门榜单)
        ├─ comment.get_comments() → 20 comments/video (串行, 1s delay)
        ├─ LLM 识别 / Heuristic 降级
        └─ 产出 2-3 条候选
```

### 已存在的可复用能力

项目已有但未与采集管道打通的两个子系统：

1. **`BilibiliDanmakuService`** (`services/live/bilibili_danmaku.py`, 369行) — 完整的实时弹幕接收器
   - 支持 `DANMU_MSG` / `SEND_GIFT` / `SUPER_CHAT` / `INTERACT_WORD` 事件
   - 独立线程 + asyncio event loop
   - 自动重连（指数退避）
   - **但整个代码库没有一行 `set_callback()` 调用** — 能力是空中楼阁

2. **`BilibiliInteractionLearner`** (`services/meme/bilibili_interaction.py`, 381行) — 弹幕交互模式分析器
   - `_collect_danmaku(room_id)` 可以拉取历史弹幕
   - LLM 分析弹幕交互模式
   - **但输出只做直播策略，不喂给采集管道**

### 主要瓶颈

| 瓶颈 | 根因 |
|------|------|
| 数据源错位 | 梗在弹幕中发酵，取的是热门榜单 |
| 串行慢 | 20视频 × 1s delay = 20s+，常超时 |
| LLM上下文贫瘠 | 只有标题+标签+评论，无弹幕 |
| Heuristic 弱 | 字符 2-gram 不是语义匹配 |
| 门槛高 | persona_fit < 0.5 丢弃，池只有10 slots |

## Goals / Non-Goals

**Goals:**
- 将实时弹幕流（`BilibiliDanmakuService`）和历史弹幕（`live.get_danmaku`）接入采集管道
- 评论获取从串行改为并行，采集时间从 ~60s 降至 ~5-10s
- Heuristic 从字符 2-gram 升级为语义级短语提取
- LLM prompt 增加弹幕分析维度，要求跨视频交叉验证
- MemePool 槽位扩容（10→20），MemeDiscoverer 候选扩容（3→15）
- 每次采集产出从 2-3 条提升至 10-20 条

**Non-Goals:**
- 不新增 B站直播功能（room_id 配置已有，只需打通）
- 不新增其他平台数据源（抖音/微博/贴吧——留待后续变更）
- 不修改 `BilibiliDanmakuService` 的核心架构（只新增接口暴露）
- 不改动 MemePool 的衰减/复活算法逻辑

## Decisions

### D1: DanmakuBuffer 组件设计

**方案**: 新增 `services/meme/danmaku_buffer.py`，作为一个轻量级内存缓冲区

```
BilibiliDanmakuService
  → on_danmaku callback
    → DanmakuBuffer.add(msg)
      → 按时间窗口管理环形缓冲区 (max 1000条)
      → 在线更新高频短语频率表
      → 提供查询接口
```

**接口**:
```python
class DanmakuBuffer:
    def __init__(self, max_size: int = 1000)
    def add(self, msg: DanmakuMessage) -> None       # 实时弹幕推入
    def get_hot_phrases(self, min_freq: int = 3, window_minutes: int = 30) -> List[DanmakuPhrase]
    def get_recent_danmaku(self, limit: int = 100) -> List[str]
    def clear(self) -> None
    @property
    def total_count(self) -> int                      # 缓冲区总弹幕数
```

**数据结构**:
```python
@dataclass
class DanmakuPhrase:
    text: str
    frequency: int
    first_seen: float
    last_seen: float
    source_room_id: int
```

**为什么不持久化到 DB？**: DanmakuBuffer 的作用是"最近弹幕的热短语"临时窗口，不需要持久化。采集管道每次运行时会消费当前缓冲区内容。历史弹幕通过 `live.get_danmaku()` 获取。

### D2: BilibiliDanmakuService 接口暴露

**方案**: `BilibiliDanmakuService` 新增一个 `set_buffer(danmaku_buffer: DanmakuBuffer)` 方法，内部 `_consume_queue` 在回调弹幕给 UI 的同时，也推入 buffer。

```python
class BilibiliDanmakuService:
    def set_buffer(self, buffer: DanmakuBuffer) -> None:
        self._danmaku_buffer = buffer
    
    # _consume_queue 中增加一行:
    # if self._danmaku_buffer:
    #     self._danmaku_buffer.add(msg)
```

**为什么不重构整个架构？**: `BilibiliDanmakuService` 运行在独立线程中，最小侵入式改动即可暴露数据。

### D3: BilibiliMemeCollector 采集改造

**采集流程变为两个并行数据源**:

```
collect()
  ├── _fetch_trending_videos()   ← 已有 (并行化评论获取)
  └── _fetch_danmaku_phrases()   ← 新增
        ├─ danmaku_buffer.get_hot_phrases()  ← 实时弹幕
        └─ live.get_danmaku(room_id)         ← 历史弹幕
              ↓
        合并 → LLM 识别
```

**参数调整**:
| 参数 | 当前值 | 改后值 |
|------|--------|--------|
| max_videos | 20 | 50 |
| max_comments_per_video | 20 | 50 |
| min_comment_likes | 3 | 2 |
| request_delay | 1.0 | 0.3 |
| request_timeout | 60 | 120 |
| comment_timeout | 10 | 15 |

**评论获取并行化**:
```python
# Before:
for video in videos:
    await asyncio.sleep(self._request_delay)
    comments = await self._fetch_comments(video.bvid)

# After:
async def fetch_one(video):
    await asyncio.sleep(self._request_delay)  # 保持礼貌速率
    return video.bvid, await self._fetch_comments(video.bvid)

results = await asyncio.gather(*[fetch_one(v) for v in videos], return_exceptions=True)
```

### D4: LLM Prompt 升级

当前 prompt 只要求分析"标题+标签+评论"。升级后增加：

1. **弹幕高频短语分析**: 喂入 DanmakuBuffer 的高频短语列表，要求 LLM 判断哪些是梗
2. **跨视频交叉验证**: 要求 LLM 标记"在多个视频弹幕/评论中出现"的模式
3. **persona_fit 改为相对排名**: 不再设绝对值门槛，改为按候选列表的相对分排序，取 top-K

新 prompt 核心变化：
```
分析要求（增加）：
- 弹幕高频短语中识别哪些具有梗的特征（重复性、变体、情绪色彩）
- 标记跨视频/跨评论出现的重复短语
- 区分"通用流行语"和"特定场景梗"
```

### D5: Heuristic 语义级升级

**当前**: `chars[i] + chars[i+1]` 字符 2-gram → 碎片无意义

**改后**: jieba 分词 + 语义 n-gram + TF-IDF 过滤

```python
import jieba
from collections import Counter
from math import log

def extract_semantic_phrases(texts: List[str], top_k: int = 20) -> List[str]:
    # 1. jieba 分词
    tokens = [list(jieba.cut(t)) for t in texts]
    # 2. 提取 2-4 个词的 n-gram
    ngrams = Counter()
    for token_list in tokens:
        for i in range(len(token_list)):
            for j in range(i+1, min(i+4, len(token_list)+1)):
                phrase = ''.join(token_list[i:j])
                if len(phrase) >= 2:
                    ngrams[phrase] += 1
    # 3. TF-IDF 过滤（去掉语料中过于通用的词）
    total_docs = len(texts)
    df = Counter()  # document frequency
    ... 
    # 4. 返回高频且有区分度的短语
```

需要新增依赖：`jieba`（纯 Python 分词库，轻量）

### D6: MemePool 和 MemeDiscoverer 扩容

| 组件 | 参数 | 当前 | 改后 |
|------|------|------|------|
| MemePool | max_active | 10 | 20 |
| MemeDiscoverer | meme_candidates_per_run | 3 | 15 |
| MemeCognitiveAnalyzer | min_persona_fit_score | 0.5 | 0.4（降低门槛） |

同时 `persona_fit` 从硬阈值改为按批次相对排名：取候选列表 top-50%。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| B站 API 限速更严重（max_videos 50 + 并行） | 保持 `request_delay=0.3` 礼貌间隔；`asyncio.gather` 加 `semaphore` 控制并发数（默认 5） |
| jieba 分词增加依赖体积 | jieba 是纯 Python 包，~15MB 词典，可延迟加载；只在 heuristic 降级路径中使用 |
| DanmakuBuffer 内存占用 | 环形缓冲区上限 1000 条，每条弹幕平均 ~200 字符 ≈ 200KB 上限，无压力 |
| 实时弹幕依赖直播间在线 | DanmakuBuffer 为空时自动降级到纯历史弹幕路径；历史弹幕走 `live.get_danmaku()` 不依赖在线 |
| 弹幕质量波动 | 弹幕中混杂大量"啊啊啊""哈哈哈"等无效内容——通过 min_freq 阈值 + LLM 过滤 |

## Open Questions

- `BilibiliDanmakuService` 的 room_id 当前如何配置的？需要确认配置入口是否已存在，还是需要在 `config/features/memory.yaml` 中新增
- `live.get_danmaku()` 获取历史弹幕是否需要 Credential（登录态）？当前 `BilibiliInteractionLearner` 调用时没有传 credential——需要验证是否工作
