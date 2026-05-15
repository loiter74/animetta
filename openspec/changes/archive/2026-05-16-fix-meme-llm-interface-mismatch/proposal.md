## Why

`bilibili_collector.py`（3 处）和 `analyzer.py`（1 处）调用 `self._llm.chat(messages=[...], response_format=...)`，使用 OpenAI 原生 API 的字典式协议。但系统注入的 `llm_client` 是 `LLMInterface` 实例，其 `chat()` 签名为 `(user_input: str, **kwargs) -> str`。`messages` 关键字参数沉入 `**kwargs` 被忽略，`user_input` 未传递导致 `TypeError`，采集到的梗无法完成 LLM 认知分析，最终 pending 始终为 0。

## What Changes

- 在 `LLMInterface` 中新增 `chat_messages()` 方法，接收 `messages: list[dict]` 和 `response_format: dict`，内部将 messages 序列化为 prompt 字符串后委托给 `chat()`
- `OpenAILLM` 覆盖 `chat_messages()`，直接调用 OpenAI 原生 `client.chat.completions.create(messages=..., response_format=...)` 保留 OpenAI 特有功能
- `bilibili_collector.py` `_identify_meme_candidates()` 改为调用 `self._llm.chat_messages(messages=..., response_format=...)`
- `analyzer.py` `analyze()` 改为调用 `self._llm.chat_messages(messages=..., response_format=...)`
- `bilibili_interaction.py` `_analyze_patterns()` 改为调用 `self._llm.chat_messages(messages=..., response_format=...)`

## Capabilities

### New Capabilities
- `llm-chat-messages`: `LLMInterface` 新增 `chat_messages()` 方法，支持 messages-based 调用协议，兼容 OpenAI 原生 response_format。所有 LLM 实现提供默认实现（prompt 序列化），OpenAILLM 提供原生覆盖

### Modified Capabilities
- `bilibili-meme-collector`: `_identify_meme_candidates()` LLM 调用协议从 OpenAI 原生 API 切换到 `LLMInterface.chat_messages()`
- `meme-cognitive-analysis`: `analyze()` LLM 调用协议从 OpenAI 原生 API 切换到 `LLMInterface.chat_messages()`

## Impact

- **代码**: `LLMInterface`（+ 抽象方法）、`OpenAILLM`（+ 覆盖实现）、`bilibili_collector.py`、`analyzer.py`、`bilibili_interaction.py`（各 1 处调用修改）
- **API**: `chat_messages()` 是新增方法，无 breaking change
- **依赖**: 无新增依赖
