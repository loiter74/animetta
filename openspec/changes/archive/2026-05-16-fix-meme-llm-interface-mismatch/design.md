## Context

当前 `LLMInterface.chat()` 签名为 `(user_input: str, **kwargs) -> str`，所有 LLM 实现（OpenAILLM、GLMLLM、OllamaLLM 等）遵循此协议。但 `src/anima/services/meme/` 下的采集器和分析器期望 OpenAI 原生 API 协议：`chat(messages=[{role, content}, ...], response_format=...)` 且返回 `{"content": "..."}` 字典。

这两个协议不兼容——meme 代码传入的 `messages` 和 `response_format` 沉入 `**kwargs` 且被完全忽略，`user_input` 未传导致 `TypeError`。

## Goals / Non-Goals

**Goals:**
- 为 `LLMInterface` 提供 messages-based 调用能力，使 meme 组件能通过标准接口调用 LLM
- `OpenAILLM` 利用其原生能力支持 `response_format={"type": "json_object"}`（强制 JSON 输出），其他 LLM 实现通过 prompt engineering 尽力而为
- 调用方代码改动最小：三处 `chat()` 调用改为 `chat_messages()`，其余逻辑不变

**Non-Goals:**
- 不修改其他 LLM 实现（GLM、Ollama 等）——它们使用默认基类实现
- 不改变 `chat()` 的签名或行为——现有所有调用者不受影响
- 不引入新的第三方依赖

## Decisions

### Decision 1: 新增 `chat_messages()` 而非修改 `chat()`

**选择**: 在 `LLMInterface` 中新增 `chat_messages(messages, **kwargs) -> str` 方法，默认实现将 messages 序列化为 prompt 字符串后委托给 `chat()`。`OpenAILLM` 覆盖此方法直接调用原生 `client.chat.completions.create()`。

**备选方案**:
- A) 修改现有 `chat()` 签名支持 messages——**否决**：会破坏所有现有调用者（graph nodes、tool handler 等 20+ 处），风险远大于收益
- B) 修改 meme 调用方传入 prompt 字符串——**否决**：丢失 `response_format={"type": "json_object"}` 能力（强制 JSON 输出对 meme 分析至关重要），且需要大幅重写 meme 组件
- C) 将 meme 组件改为接收原生 OpenAI client——**否决**：破坏依赖注入架构，meme 组件与 OpenAI 耦合

**理由**: 新增方法是标准的扩展模式，零 breaking change，保留两种调用风格各自的最优实现。

### Decision 2: 默认实现策略——prompt 序列化

**选择**: 基类 `chat_messages()` 默认实现将 `messages` 列表拼接为单个 prompt 字符串：
```python
prompt = "\n".join(f"[{m['role']}]: {m['content']}" for m in messages)
return await self.chat(prompt, **kwargs)
```

**理由**: 
- 简单可靠，对所有 LLM 实现通用
- `response_format` kwarg 在默认实现中忽略（仅 OpenAI 支持），调用方可自行解析返回字符串中的 JSON
- 当 `llm_client` 不是 OpenAI 时，降级行为明确

### Decision 3: OpenAILLM 原生覆盖

**选择**: `OpenAILLM.chat_messages()` 直接调用 `self.client.chat.completions.create(messages=..., response_format=..., ...)`，绕过内部的 `_build_messages()` 和 conversation history 管理。返回 `response.choices[0].message.content` 字符串。

**理由**:
- 保留 `response_format={"type": "json_object"}` 能力——对 meme 分析至关重要（强制 JSON 输出，避免解析失败）
- 利用 OpenAI 原生 messages 格式——保留 system/user/assistant role 语义
- 该覆盖实现与 `chat()` 内已有的 `self.client.chat.completions.create()` 调用模式一致，代码复用度高

## Risks / Trade-offs

- **[Risk] OpenAILLM.chat_messages() 不经过 conversation history** → meme 采集和分析是独立任务，不依赖对话历史，此行为符合预期。如需历史上下文，调用者可在 messages 中显式添加
- **[Risk] 非 OpenAI LLM 的 response_format 不被支持** → 降级为 prompt 序列化 + 纯文本返回。meme 分析器已通过 `_parse_llm_json()` 处理非 JSON 返回，降级路径存在
- **[Trade-off] 抽象层增加** → `LLMInterface` 多一个方法，增加 5 行抽象代码。对比 meme 组件 3 处 bug 修复的收益，trade-off 可接受
