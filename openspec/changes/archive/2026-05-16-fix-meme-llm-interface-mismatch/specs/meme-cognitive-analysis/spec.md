# meme-cognitive-analysis Delta Specification

## MODIFIED Requirements

### Requirement: 梗认知分析

系统 SHALL 对每个梗候选执行 LLM 驱动的认知分析，输出结构化分析结果。LLM 调用 SHALL 使用 `LLMInterface.chat_messages()` 方法。

#### Scenario: 认知分析执行
- **WHEN** BilibiliMemeCollector 产出梗候选列表
- **THEN** 系统调用 LLM 进行认知分析
- **AND** LLM 调用 SHALL 通过 `self._llm.chat_messages(messages=[...], response_format={"type": "json_object"})` 发起
- **AND** LLM 的 system prompt 要求输出 JSON 格式
- **AND** 分析维度 SHALL 包含：幽默机制（humor_mechanism）、触发场景（context_trigger）、情感色彩（emotional_tone）、人设匹配度（persona_fit_score）、使用示例（usage_example）

#### Scenario: 认知分析 JSON Schema 校验
- **WHEN** LLM 返回认知分析结果
- **THEN** 系统 SHALL 校验 JSON 格式的完整性
- **AND** 必填字段缺失时标记该候选为"分析失败"
- **AND** persona_fit_score SHALL 为 0-1 之间的浮点数

#### Scenario: 认知分析失败降级
- **WHEN** `chat_messages()` 调用失败或返回无法解析的结果
- **THEN** 系统 SHALL 创建仅有基础字段（text + context_hint）的 Meme
- **AND** cognitive_analysis 字段设为 None
- **AND** 记录 warning 日志
