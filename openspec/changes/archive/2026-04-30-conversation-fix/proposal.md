## Why

修复 AI 对话时前端不显示 AI 回复的问题。用户在聊天界面发送消息后只能看到自己的输入，AI 的回答始终不出现。

## What Changes

- 修复 `OpenAILLM` 缺少 `chat_with_tools` 方法（LangGraph 工具调用路径崩溃）
- 修复 `DeepSeekLLMConfig` 被 `OpenAILLM.from_config` 拒绝，导致静默降级为 `MockLLM`（不产生真实回复）
- 修复 `OpenAILLM.chat_stream` 忽略传入的 `system_prompt` 参数（RAG 记忆增强上下文丢失）
- 修复 `.env` 文件从未被加载，`${VAR}` 环境变量占位符无法展开
- 修复 `services.yaml` 中 `openai:` 段缺少 key 名的 YAML 格式错误
- 修复前端 `finalizeResponse` 竞态条件：后端发出 `is_complete` 消息时流式消息尚未创建，回复被丢弃

## Capabilities

### New Capabilities
- `conversation-fix`: 覆盖后端 LLM 集成修复、配置加载修复和前端消息显示修复

### Modified Capabilities

无。本 change 不涉及 spec 级行为变更，仅修复现有功能的 bug。

## Impact

- `src/anima/services/intelligence/llm/openai_llm.py`: 新增 `chat_with_tools`、`_convert_tools_to_openai`、`_build_langchain_messages`；修改 `from_config` 改为 `getattr` 属性提取以兼容 DeepSeek；修改 `chat_stream`/`chat`/`_build_messages` 支持动态 `system_prompt`
- `src/anima/config/app.py`: 新增 `_load_env_file()` 自动加载 `.env`；集成 `python-dotenv`
- `config/services.yaml`: 修复 `openai:` 段 YAML 缩进
- `frontend/src/stores/chat.ts`: 修复 `finalizeResponse` 中流式消息未创建时的处理分支
