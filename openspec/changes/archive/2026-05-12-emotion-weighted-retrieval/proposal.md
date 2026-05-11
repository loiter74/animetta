## Why

Anima 已有 Emotion analyzer 在对话中标注情绪，但这个信息**完全没有被用于记忆检索**。从认知科学看，人脑的杏仁核-海马体交互让高情绪事件记得更牢（flashbulb memory）。情绪标签是记忆检索的天然权重信号，但目前被闲置。

## What Changes

- 在 `MemoryManager.search()` / `hybrid_search()` 中，对返回结果按情绪权重重排序
- 高情绪值的记忆提升检索排名（语义 + 关键词 + 情绪三路融合）
- 情绪衰减速度与情绪值成反比：高情绪记忆遗忘更慢
- 已有 emotion tag 的 MemoryEntry 自动受益

## Capabilities

### New Capabilities
- `emotion-weighted-retrieval`: 记忆检索结果按情绪标签加权排序。关键行为：高情绪事件检索排名更高、衰减更慢。不改变存储层，只改检索排序。

## Impact

- `src/anima/memory/search/hybrid.py`: 增加情绪权重信号
- `src/anima/memory/search/scorer.py`: 增加情绪打分
- `src/anima/memory/models/memory_entry.py`: 可能需要增加情绪字段
- 不影响存储层，纯检索层改动
