## Context

AI 对话链路: 前端发送文本 → Socket.IO → `orchestrator.process_text()` → LangGraph 状态图 (`llm_node` → `tts_node` → `emotion_node` → `output_node`) → Socket.IO `sentence` 事件 → 前端 `useChat` 显示。

该链路中发现了多处断裂：后端 LLM 工厂因类型检查失败静默降级为 MockLLM（不产生真实回复），`.env` 文件从未加载导致 API Key 为空，`OpenAILLM` 缺少工具调用接口，以及前端 `finalizeResponse` 竞态条件导致回复被丢弃。

## Goals / Non-Goals

**Goals:**
- 修复后端 LLM 调用链，使 DeepSeek/OpenAI 配置能正确产生 AI 回复
- 确保 `.env` 文件的 API Key 能被自动加载到配置中
- 修复前端消息显示逻辑，确保所有 `sentence` 事件都能正确渲染
- 所有修改为最小修复，不引入新功能

**Non-Goals:**
- 不改变现有架构或数据流
- 不新增 LLM 提供商
- 不修改 TTS/ASR/VAD 等其他服务

## Decisions

1. **`from_config` 类型检查改为属性提取** — 原代码 `isinstance(config, OpenAILLMConfig)` 拒绝了 `DeepSeekLLMConfig`。改用 `getattr(config, field, default)` 提取公共字段，兼容所有 OpenAI API 兼容的配置类。

2. **`.env` 加载放在 `from_yaml()` 入口** — 在配置解析之前执行 `load_dotenv()`，确保 `${VAR}` 占位符能正确展开。按优先级搜索 `ANIMA_ENV_FILE` > `cwd/.env` > 项目根目录 `.env`。

3. **`chat_with_tools` 复用 GLMLLM 相同接口签名** — 返回 `{content, tool_calls}` 字典，格式与 `GLMToolConverter.parse_tool_response` 一致，使 `_llm_with_tools` 能统一处理。

4. **前端 `finalizeResponse` 增加 `else if` 分支** — 当前端收到 `is_complete` 但流式消息尚未通过 `scheduleFlush` 创建时，直接创建 `status: 'complete'` 的 assistant 消息，不等待 500ms flush。

## Risks / Trade-offs

- `getattr` 方式少了编译期类型检查，但所有字段都是运行时从配置对象读取的，安全性等价
- `.env` 只加载一次（通过函数属性缓存），后续手动修改 `.env` 需要重启后端
- 前端修改不改变 `scheduleFlush` 的 500ms 延迟，正常流式场景不受影响
