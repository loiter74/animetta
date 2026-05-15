# llm-chat-messages Specification

## Purpose
为 `LLMInterface` 提供 messages-based 调用协议，允许调用方以 `[{role, content}, ...]` 格式传递消息，兼容 OpenAI 原生 `response_format` 功能，同时保持与现有 `chat(user_input: str)` 接口的向后兼容。

## ADDED Requirements

### Requirement: LLMInterface.chat_messages() 默认实现

`LLMInterface` SHALL 提供 `chat_messages(messages: list[dict], **kwargs) -> str` 方法，默认实现将 messages 列表序列化为 prompt 字符串后委托给 `chat()`。

#### Scenario: 默认 prompt 序列化
- **WHEN** 调用 `chat_messages(messages=[{"role": "system", "content": "你是一个助手"}, {"role": "user", "content": "你好"}])`
- **THEN** 系统 SHALL 将 messages 拼接为 `"[system]: 你是一个助手\n[user]: 你好"` 格式的字符串
- **AND** 调用 `self.chat(prompt, **kwargs)` 并返回结果

#### Scenario: 非 OpenAI LLM 忽略 response_format
- **WHEN** 调用 `chat_messages(messages=[...], response_format={"type": "json_object"})` 且 LLM 实例不是 OpenAILLM
- **THEN** `response_format` kwarg SHALL 被传入 `chat()` 的 `**kwargs` 但被忽略
- **AND** 返回纯文本字符串（调用方自行解析 JSON）

### Requirement: OpenAILLM.chat_messages() 原生覆盖

`OpenAILLM` SHALL 覆盖 `chat_messages()`，直接调用 `self.client.chat.completions.create(messages=..., response_format=..., model=..., temperature=...)` 保留 OpenAI 原生能力。

#### Scenario: 原生 messages + response_format 调用
- **WHEN** 调用 `openai_llm.chat_messages(messages=[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}], response_format={"type": "json_object"})`
- **THEN** 系统 SHALL 直接调用 `self.client.chat.completions.create(messages=messages, response_format={"type": "json_object"})`
- **AND** 返回 `response.choices[0].message.content`
- **AND** 不经过 `_build_messages()` 或 conversation history

#### Scenario: OpenAILLM.chat_messages() 支持 model/temperature 覆写
- **WHEN** 调用 `openai_llm.chat_messages(messages=[...], model="gpt-4o", temperature=0.3)`
- **THEN** `model` 和 `temperature` SHALL 被传递给 `client.chat.completions.create()`
- **AND** 若未提供则使用实例默认值
