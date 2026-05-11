## Context

Persona prompt 是静态 YAML，角色行为不会根据交互反馈进化。参考 LangMem `prompt_optimizer` 的 gradient 算法思路。

## Decisions

- **触发时机**：PeriodicLearner 定时触发，不在实时对话中
- **输出形式**：YAML 建议文件，不自动应用。设置 `auto_apply_threshold` 开关
- **算法**：Gradient-style：分析 → 生成调整建议 → 输出 reviewable file
