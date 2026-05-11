## Context

Emotion analyzer 在对话中标注情绪值，但检索排序忽略了这个信号。需要在混合搜索的分数融合中增加情绪权重。

## Decisions

- **权重计算**：`emotion_weight = 1.0 + emotion_intensity * 0.5`（高情绪 +50% 提权）
- **衰减速度**：`decay_rate = base_rate / (1.0 + emotion_intensity)`（高情绪衰减更慢）
- **集成方式**：在 `scorer.py` 中注入，不影响 `hybrid.py` 的两路召回
