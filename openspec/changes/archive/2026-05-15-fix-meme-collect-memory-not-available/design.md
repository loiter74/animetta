## Context

当前 `ServiceContext` 采用懒创建策略——仅在 `_get_or_create_orchestrator()` 被调用时（即首次聊天消息）才创建 session 上下文。但 meme 相关 WebSocket handler（`on_meme_collect`、`on_meme_list` 等）直接使用 `get_context(sid)`，不触发创建。导致未发过消息的客户端点击梗筛选必然失败。

此外在两个次级问题：
- `on_meme_list` 的守卫条件比其他 5 个 meme handler 少一个 `or not ctx.memory_system.meme_pool` 检查，在 `meme_pool` 为 None 的降级场景会穿透守卫后 crash
- `ServiceContext.init_memory()` 构建的 config dict 缺少 `meme_pool`/`learner`/`scheduler`/`llm_client` 字段，导致 `MemorySystem` 的子组件因缺配置而静默降级

## Goals / Non-Goals

**Goals:**
- 确保 `on_meme_collect` 在任何页面状态下（包括首连后立即使用）都能正常触发 B 站梗采集
- 统一 6 个 meme handler 的空值守卫逻辑，消除 `on_meme_list` 的穿透 bug
- 将 `memory.yaml` 中完整的配置节透传给 `MemorySystem`，避免因缺配置导致的次级组件静默降级

**Non-Goals:**
- 不改变 `ServiceContext` 的整体懒创建策略（不改为连接时立即创建）
- 不引入新的 REST API 或 WebSocket 事件
- 不改动 `MemorySystem` 内部的构造函数或异常处理逻辑

## Decisions

### Decision 1: `on_meme_collect` 通过 `_get_or_create_orchestrator()` 懒创建上下文

**选择**: 在 `get_context()` 返回 None 时，调用已有的 `_get_or_create_orchestrator(sid)` 方法，该方法内部调用 `get_or_create_context() → init_memory()`。

**备选方案**:
- A) 直接调用 `self.session_manager.get_or_create_context(sid, config, send_callback)` — 可行但需要在 `on_meme_collect` 中重复构造 `config` 和 `send_callback`，增加冗余代码
- B) 在 `on_connect` 时创建上下文 — 改动面大，违背懒创建策略，可能引入不必要的资源消耗

**选择 A 的理由**: `_get_or_create_orchestrator` 已封装了 config 加载和 callback 构造，且 orchestrator 创建是幂等的。虽然会多创建一个 orchestrator 对象（对 meme-only 场景非必需），但消除了代码重复，且 orchestrator 创建开销很小（无 LLM/ASR 调用）。

### Decision 2: 补全 `on_meme_list` 的空值检查

**选择**: 在 line 683 的守卫条件中追加 `or not ctx.memory_system.meme_pool`，与 `on_meme_add`（line 583）、`on_meme_rate`（line 620）等完全一致。

**备选方案**:
- A) 同样改为懒创建 + 补空值检查 — 改动量大，且绝大多数场景下 `init_memory()` 成功后 `meme_pool` 不为 None
- B) 仅补空值检查 — `on_meme_list` 的业务场景是「列出待筛选梗」，若上下文不存在返回空列表比返回错误信息 UX 更差（用户无法区分「没有梗」和「系统未就绪」）

**选择 B 的理由**: 最小改动，保持事件响应的语义一致性（error 表示系统问题，空数组表示无数据）。`on_meme_list` 返回 `MemePool 未初始化` 比空数组更适合——让用户知道需要先连接/发消息。

### Decision 3: 透传完整 `memory.yaml` 配置到 `MemorySystem`

**选择**: 在 `init_memory()` 构建 config dict 时，增加 `meme_pool`、`learner`、`scheduler` 三个 section，以及 `llm_client: self.llm_engine`。

**修改前**:
```python
config = {
    "workspace_dir": ...,
    "short_term_max_turns": ...,
    "search": mem_cfg.get('search', {}),
    "chunk": mem_cfg.get('chunk', {}),
}
```

**修改后**:
```python
config = {
    "workspace_dir": ...,
    "short_term_max_turns": ...,
    "search": mem_cfg.get('search', {}),
    "chunk": mem_cfg.get('chunk', {}),
    "meme_pool": mem_cfg.get('meme_pool', {}),
    "learner": mem_cfg.get('learner', {}),
    "scheduler": mem_cfg.get('scheduler', {}),
    "llm_client": self.llm_engine,
}
```

**理由**: `MemorySystem.__init__` 已支持这些 key（通过 `config.get()` 带默认值），只是之前从未被传入。透传后 `PeriodicLearner` 能拿到 `llm_client`（用于 LLM 分析梗候选），`MemePool` 和 `Scheduler` 能拿到完整配置（如时间衰减参数、调度间隔）。向后兼容——若 YAML 中缺少某 section 则使用 MemorySystem 内置默认值。

## Risks / Trade-offs

- **[Risk] `_get_or_create_orchestrator` 额外创建 orchestrator** → 在 meme-only 场景（用户从未发消息），会额外创建一个 `LangGraphOrchestrator` 实例。Mitigation：orchestrator 创建开销很小（约 50ms，无 LLM 调用），且后续发消息时可复用已有实例。
- **[Risk] `llm_client` 可能为 None** → 若 session 尚未初始化 LLM engine，`llm_client` 为 None。Mitigation：`MemorySystem.__init__` 中 `learner_config.get("enabled", True) and llm_client is None` 时 `PeriodicLearner` 会静默失败（logged as warning），与当前行为一致（不会更差）。
- **[Trade-off] 懒创建 vs 连接时创建** → 保持懒创建，意味着首次 meme 操作仍需 trigger 上下文初始化（~200ms）。Mitigation：相比于连接时立即初始化所有 session 的开销，懒创建更节省资源。考虑到 meme 功能使用频率远低于聊天，该 trade-off 可接受。
