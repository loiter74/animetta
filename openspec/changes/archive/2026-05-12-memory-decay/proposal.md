## Why

Anima 的 MemoryEntry 系统（事实存储 + 版本链）没有遗忘机制。所有事实永久保留且被平等对待。从认知科学看，这违背了艾宾浩斯遗忘曲线——遗忘是自适应功能：过滤噪音、提炼重要信息、为新模式腾出空间。Mem0 的 ADD-only 也是同样问题。Anima 已有 MemePool 的时间衰减机制，但这个模式没有推广到主记忆系统。

## What Changes

- 给 MemoryEntry 增加衰减函数：`decay = f(time_since_created, emotion_value, retrieval_frequency)`
- 低情绪值 + 低检索频率 + 时间久 → 加速衰减 → 检索排名降低 → 最终归档
- 高情绪值 + 高检索频率 → 衰减缓慢 → "巩固"为长期记忆
- 不物理删除，只做"归档"标记，保持可审计性

## Capabilities

### New Capabilities
- `memory-decay`: MemoryEntry 按时间、情绪、检索频率三星号衰减。关键行为：低价值记忆自动降权并最终归档，高价值记忆巩固。不物理删除，保持 Wiki Markdown 可审计性。

## Impact

- `src/anima/memory/models/memory_entry.py`: 增加衰减相关字段
- `src/anima/memory/search/scorer.py`: 增加衰减权重因子
- `src/anima/memory/manager.py`: 增加归档逻辑
- 不影响存储层结构，只加字段和检索权重
