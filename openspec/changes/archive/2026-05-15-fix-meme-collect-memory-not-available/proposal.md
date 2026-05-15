## Why

点击梗筛选页的「采集热梗」按钮后返回 "Memory system not available" 错误。根因是 `ServiceContext` 只在首次聊天消息时懒创建，而 `on_meme_collect` 等 meme WebSocket handler 使用 `get_context()`（只取不建），导致新连接的、未发过消息的客户端永远触发该错误。

同时 `on_meme_list` 缺少 `meme_pool is None` 的空值检查（其他 5 个 meme handler 都有），`ServiceContext.init_memory()` 传给 `MemorySystem` 的 config dict 缺少 `meme_pool`/`learner`/`scheduler` key。

## What Changes

- `admin_handlers.py` `on_meme_collect`: `get_context()` → 若为 None 则先调用 `_get_or_create_orchestrator()` 创建上下文
- `admin_handlers.py` `on_meme_list`: 补充 `or not ctx.memory_system.meme_pool` 空值检查，与其余 5 个 meme handler 一致
- `service_context.py` `init_memory()`: 将 `memory.yaml` 中 `meme_pool`/`learner`/`scheduler` 配置节透传给 `MemorySystem`，避免次级组件因缺配置而静默降级

## Capabilities

### New Capabilities
<!-- None -- this is a bug fix, no new capabilities introduced -->

### Modified Capabilities
- `meme-review-api`: Socket.IO meme handler（`on_meme_collect`、`on_meme_list`）现在支持在未有聊天交互时懒创建 session 上下文，而非直接返回错误
- `bilibili-meme-collector`: `on_meme_collect` 触发路径现在可在任意页面状态（包括首次连接后立即使用）下正常工作

## Impact

- **代码**: `src/anima/orchestration/server/handlers/admin_handlers.py`（2 处修改），`src/anima/core/service_context.py`（1 处修改）
- **API**: 无 breaking change。WebSocket 事件响应格式不变，仅原先返回 error 的场景改为正常返回
- **依赖**: 无新增依赖
