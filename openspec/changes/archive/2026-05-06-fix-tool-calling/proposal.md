## Why

Tool calling (web_search, calculator, etc.) is silently broken. The `LLMFactory` wraps all LLM services in `TracingProxy` for OpenTelemetry tracing, but `LLMChatModelAdapter` uses Pydantic with strict `is_instance_of` validation requiring `LLMInterface`. `TracingProxy` is not an `LLMInterface` subclass, so `create_chat_model_from_service()` always fails and `chat_model` is always None. Every session with tools enabled silently falls back to no-tool mode.

## What Changes

- Fix `create_chat_model_from_service()` in `langchain_adapter.py` to unwrap dynamic proxies (TracingProxy) before creating the Pydantic ChatModel adapter
- No changes to TracingProxy, LLMInterface, or Pydantic model definitions

## Capabilities

### New Capabilities
- `tool-calling`: Core tool calling capability — LLM can invoke built-in tools (web_search, calculator, get_current_time) during conversations

### Modified Capabilities
None — bug fix, no existing spec changes

## Impact

- `src/anima/services/intelligence/llm/langchain_adapter.py`: ~5 lines added in `create_chat_model_from_service()` to unwrap TracingProxy
- No new dependencies, no breaking changes, no config changes
- Tool calling becomes functional for all sessions
