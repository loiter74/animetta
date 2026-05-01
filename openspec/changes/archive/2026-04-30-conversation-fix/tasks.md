## 1. Backend: LLM Engine Fixes

- [x] 1.1 Fix `DeepSeekLLMConfig` → `OpenAILLM` type check in `from_config()` — replace `isinstance` check with `getattr` field extraction
- [x] 1.2 Add `chat_with_tools()` method to `OpenAILLM` — with `_convert_tools_to_openai()` and `_build_langchain_messages()` helpers
- [x] 1.3 Fix `OpenAILLM.chat_stream()` and `chat()` to forward `system_prompt` kwarg to `_build_messages()`

## 2. Backend: Configuration Loading

- [x] 2.1 Add `_load_env_file()` function in `app.py` — auto-load `.env` via `python-dotenv` before config expansion
- [x] 2.2 Fix YAML indentation error in `config/services.yaml` — add missing `openai:` key

## 3. Frontend: Chat Display

- [x] 3.1 Fix `finalizeResponse()` race condition in `chat.ts` — add `else if (currentResponse.value)` branch to create assistant message directly when `scheduleFlush` hasn't fired yet
