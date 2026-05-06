## Context

The data flow for tool calling is:

```
LLMFactory.create_from_config()
  → TracingProxy(OpenAILLM, service_name="llm")    ← OTel tracing wrapper
  → ServicePool stores TracingProxy
  → Session.get_or_create_context()
    → ctx.load_cache(llm_engine=TracingProxy)
  → ToolManager._create_chat_model()
    → create_chat_model_from_service(llm_service=TracingProxy)
    → LLMChatModelAdapter(llm_service=TracingProxy)
    → Pydantic: isinstance(TracingProxy, LLMInterface)? → False!
    → ValidationError → returns None
```

The `chat_model` being None means `llm_node.py:174` takes the `else` branch and skips tool calling entirely.

`TracingProxy` is a generic dynamic proxy (uses `__getattr__` to delegate) that wraps any service for OTel span creation. It is NOT a subclass of `LLMInterface`. The Pydantic `LLMChatModelAdapter` model uses `llm_service: LLMInterface = Field(...)` which triggers `is_instance_of` validation.

The `chat_model` is only used for tool binding (`chat_model.bind_tools(tools)`) and as a source for `bound_tools` in `_llm_with_tools`. Actual LLM calls always go through `llm_engine` (the TracingProxy), not through `chat_model`. So unwrapping the proxy for the ChatModel does NOT lose tracing on actual LLM calls.

## Goals / Non-Goals

**Goals:**
- Make `create_chat_model_from_service()` accept TracingProxy-wrapped LLM services
- Enable tool calling for all sessions using the ServicePool
- Keep OTel tracing on actual LLM API calls

**Non-Goals:**
- No changes to TracingProxy or its relationship with LLMInterface
- No changes to LLMChatModelAdapter's Pydantic model definition
- No new dependencies

## Decisions

### Fix: Unwrap TracingProxy in `create_chat_model_from_service`

**What**: Add proxy detection and unwrapping at the start of `create_chat_model_from_service()` in `langchain_adapter.py`.

```python
def create_chat_model_from_service(llm_service, enable_tooling=False):
    # Dynamic proxies (TracingProxy) wrap LLMInterface but fail Pydantic's
    # strict isinstance check — unwrap before creating the adapter.
    if hasattr(llm_service, '_target'):
        llm_service = llm_service._target
    ...
```

**Rationale**:
- Minimal change (2 lines) in a single file
- Uses duck-typing (`hasattr('_target')`) — doesn't import TracingProxy directly
- `_target` attribute is set via `object.__setattr__` in TracingProxy.__init__, accessible via normal attribute access
- Does NOT affect actual LLM calls — `chat_model` is only for tool binding
- OTel tracing continues to work because `llm_engine` (used in `_llm_with_tools` and `_llm_without_tools`) still points to the TracingProxy

**Alternatives considered**:

1. **Store raw LLMInterface in ServicePool**: Rejected. Would lose tracing on ALL LLM calls across all sessions, not just ChatModel binding.

2. **Make TracingProxy a virtual subclass of LLMInterface via `ABC.register()`**: Rejected. TracingProxy is a generic proxy that wraps TTS and ASR too — registering it as LLMInterface would cause false positives.

3. **Change LLMChatModelAdapter to `llm_service: Any`**: Rejected. Weakens type safety for all future uses of the adapter.

4. **Wrap LLMInterface in a protocol/typing.Protocol**: Over-engineering for a 2-line fix.

## Risks / Trade-offs

- **[Risk] `_target` attribute name is a TracingProxy implementation detail**: If TracingProxy renames `_target`, this breaks. **Mitigation**: Low likelihood; the attribute name is stable as it's used internally. Adding a comment linking to TracingProxy reduces confusion.
- **[Risk] Other dynamic proxies**: If another proxy wraps LLMInterface, the same issue occurs. **Mitigation**: The duck-type check `hasattr('_target')` is generic enough to catch any TracingProxy-like wrapper.
