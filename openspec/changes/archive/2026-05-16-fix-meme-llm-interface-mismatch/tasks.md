## 1. LLMInterface — 新增 chat_messages() 默认实现

- [x] 1.1 在 `LLMInterface`（interface.py）中新增 `async def chat_messages(self, messages: list[dict], **kwargs) -> str` 方法，默认实现将 messages 序列化为 prompt 字符串后委托给 `self.chat()`
- [x] 1.2 默认序列化格式：`"\n".join(f"[{m['role']}]: {m['content']}" for m in messages)` — 将 role 作为前缀，content 作为正文

## 2. OpenAILLM — 覆盖 chat_messages() 原生实现

- [x] 2.1 在 `OpenAILLM`（openai_llm.py）中覆盖 `chat_messages()`，直接调用 `self.client.chat.completions.create(messages=messages, response_format=kwargs.get("response_format"), model=kwargs.get("model", self.model), temperature=kwargs.get("temperature", self.temperature))`
- [x] 2.2 返回 `response.choices[0].message.content`（与其他方法一致的字符串返回）
- [x] 2.3 `response_format` 仅在 kwargs 中存在时传递（允许调用方省略）

## 3. bilibili_collector.py — 切换到 chat_messages()

- [x] 3.1 `_identify_meme_candidates()`（line 366）将 `await self._llm.chat(messages=[...], response_format=...)` 改为 `await self._llm.chat_messages(messages=[...], response_format=...)`
- [x] 3.2 保持 `result.get("content", "")` 兼容逻辑——当 llm_client 是 OpenAILLM 时返回 str，不需要 dict 兼容（简化可后续单独做）

## 4. analyzer.py — 切换到 chat_messages()

- [x] 4.1 `analyze()`（line 111）将 `await self._llm.chat(messages=[...], response_format=...)` 改为 `await self._llm.chat_messages(messages=[...], response_format=...)`
- [x] 4.2 保持 `result.get("content", "")` 兼容逻辑

## 5. bilibili_interaction.py — 切换到 chat_messages()

- [x] 5.1 `_analyze_patterns()`（line 276）将 `await self._llm.chat(messages=[...], response_format=...)` 改为 `await self._llm.chat_messages(messages=[...], response_format=...)`

## 6. 验证

- [x] 6.1 运行 `PYTHONPATH=src python -m pytest tests/ -v -k "meme or llm"` — 389 passed, 0 failed（同步更新了 3 个 test 文件中的 mock: `chat` → `chat_messages`）
- [ ] 6.2 手动测试：重启后端 → 进入梗筛选页 → 点击采集热梗 → 确认不再出现 "LLM identification failed" 和 "LLM analysis failed"，pending meme 数量 > 0
