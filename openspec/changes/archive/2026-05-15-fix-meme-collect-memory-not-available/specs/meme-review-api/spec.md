# meme-review-api Delta Specification

## MODIFIED Requirements

### Requirement: Socket.IO Meme Handler 守卫条件统一

所有 meme 相关的 Socket.IO handler（`on_meme_add`、`on_meme_rate`、`on_meme_delete`、`on_meme_list`、`on_meme_review`、`on_meme_dataset`）SHALL 使用一致的守卫条件：
`not ctx or not ctx.memory_system or not hasattr(ctx.memory_system, "meme_pool") or not ctx.memory_system.meme_pool`

#### Scenario: on_meme_list 守卫条件与其他 handler 一致
- **WHEN** 前端发送 `meme:list` 事件且 `ctx.memory_system.meme_pool` 为 None
- **THEN** 系统 SHALL 返回 `{"memes": [], "error": "MemePool 未初始化"}`
- **AND** 不会因访问 `None.meme_pool.store` 而抛出 AttributeError

### Requirement: Socket.IO Meme Collect 懒创建上下文

`on_meme_collect` handler SHALL 在 session 上下文不存在时自动创建上下文，而非返回 "Memory system not available" 错误。

#### Scenario: 新连接客户端点击采集热梗
- **WHEN** 客户端已连接 WebSocket 但从未发送过聊天消息（ServiceContext 未创建）
- **AND** 前端发送 `meme:collect` 事件
- **THEN** 系统 SHALL 自动调用 `get_or_create_context()` 创建 session 上下文
- **AND** 初始化 MemorySystem（包括 MemePool）
- **AND** 调用 `learner.collect_bilibili_memes()` 执行采集
- **AND** 返回 `{"ok": True, "count": <pending_count>, "ingested": <ingested_count>}`

#### Scenario: 已建立会话的客户端点击采集热梗
- **WHEN** 客户端已发送过聊天消息（ServiceContext 已存在）
- **AND** 前端发送 `meme:collect` 事件
- **THEN** 系统 SHALL 直接复用已有上下文
- **AND** 不重复创建 ServiceContext 或 MemorySystem

#### Scenario: 记忆系统初始化失败
- **WHEN** 客户端发送 `meme:collect` 事件
- **AND** 上下文创建后 `memory_system` 仍为 None（配置禁用或初始化异常）
- **THEN** 系统 SHALL 返回 `{"ok": False, "error": "Memory system not available"}`

## ADDED Requirements

### Requirement: MemorySystem 配置透传

`ServiceContext.init_memory()` SHALL 将 `memory.yaml` 中 `meme_pool`、`learner`、`scheduler` 配置节（若存在）和 `llm_client`（session LLM engine）透传给 `MemorySystem` 构造函数。

#### Scenario: memory.yaml 包含完整 meme/learner/scheduler 配置
- **WHEN** `config/features/memory.yaml` 中存在 `meme_pool`、`learner`、`scheduler` sections
- **AND** `ServiceContext.init_memory()` 被调用
- **THEN** 这些配置节 SHALL 被包含在传给 `MemorySystem.__init__()` 的 config dict 中
- **AND** `llm_client` SHALL 被设置为 `self.llm_engine`

#### Scenario: memory.yaml 缺少某配置节
- **WHEN** `memory.yaml` 中缺少 `meme_pool` section
- **THEN** 传给 `MemorySystem` 的 `meme_pool` 字段 SHALL 为空 dict `{}`
- **AND** `MemorySystem` 使用内置默认值初始化 MemePool（行为与当前一致）
