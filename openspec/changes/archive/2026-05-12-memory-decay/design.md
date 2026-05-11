## Context

MemoryEntry 永久保留且平等对待，缺少人脑式的遗忘机制。Anima 已有 MemePool 时间衰减，需推广到主记忆系统。

## Decisions

- **衰减公式**：`decay_score = e^(-λt)` where `λ = base_rate / (emotion_intensity * retrieval_count + ε)`
- **不物理删除**：衰减到阈值以下 → 标记 archived → 默认搜索排除 → Wiki Markdown 保留审计
- **检索频率加成**：每次被检索 → `retrieval_count++` → 减缓衰减（"巩固效应"）
