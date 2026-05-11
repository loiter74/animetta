## Why

Anima 的 Persona 系统（YAML + system prompt）是**完全静态的**——角色行为模式不会通过交互进化。从认知科学看，这等于没有"程序性记忆"——通过重复经验自动调整行为的能力。角色应该能从对话反馈中学习哪些回应风格更有效、哪些行为模式需要调整。

## What Changes

- 新增 Persona Evolution Engine：定期分析对话日志，评估 persona prompt 的有效性
- 基于分析结果，自动生成 Persona Prompt 的微调建议（非自动应用，需人工审核或设置自动阈值）
- 不改变现有 Persona YAML 结构，只增加"演化层"（override 而非替换）
- 参考 LangMem `prompt_optimizer` 的 gradient 算法思路

## Capabilities

### New Capabilities
- `persona-evolution`: Persona Prompt 按对话反馈自动演化。关键行为：定时分析 → 生成调整建议 → 可选自动应用。不影响现有 Persona 基础配置。

## Impact

- `src/anima/config/persona/`: 新增 evolution 配置
- `src/anima/memory/learner/`: 新增 persona optimizer 模块
- 新增 LLM 调用（定时，非实时）
- 不改变对话响应延迟
