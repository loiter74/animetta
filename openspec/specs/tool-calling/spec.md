### Requirement: ChatModel accepts TracingProxy-wrapped LLM services
The `create_chat_model_from_service` function SHALL unwrap dynamic proxies (such as TracingProxy) before creating the LLMChatModelAdapter, so that Pydantic's isinstance validation does not reject the proxy.

#### Scenario: TracingProxy is unwrapped before ChatModel creation
- **WHEN** `create_chat_model_from_service` is called with a `TracingProxy` wrapping an `LLMInterface`
- **THEN** the function SHALL detect the proxy and extract the underlying `LLMInterface` instance
- **THEN** `LLMChatModelAdapter` SHALL be created successfully with the raw `LLMInterface`

#### Scenario: Raw LLMInterface still works unchanged
- **WHEN** `create_chat_model_from_service` is called with a direct `LLMInterface` instance (no proxy)
- **THEN** the function SHALL pass it through unchanged
- **THEN** `LLMChatModelAdapter` SHALL be created successfully

### Requirement: Tool calling works end-to-end
When ChatModel creation succeeds with bound tools, the LLM node SHALL invoke tools during conversation.

#### Scenario: LLM calls tool via ChatModel binding
- **WHEN** a user message triggers a tool call (e.g., "搜索今天的新闻")
- **THEN** the LLM node SHALL detect tool_calls in the LLM response
- **THEN** the tool_node SHALL execute the requested tool
- **THEN** the LLM SHALL incorporate the tool result into its response
