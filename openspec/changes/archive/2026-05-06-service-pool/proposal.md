## Why

当前每个用户会话都从零初始化所有服务（LLM、TTS、ASR、VAD、Memory），即使 prewarm 后首次加载仍需 ~8s，因为 prewarm 创建的引擎在 close() 时被销毁了。对于 API 型无状态服务（LLM、TTS、ASR），这些引擎完全可以全局共享，每个会话只需创建自己有状态的 VAD 和 Memory。

## What Changes

- 新增 `ServicePool` 单例：在服务器启动时初始化 LLM/TTS/ASR 引擎并永久持有
- 修改 `SessionManager.get_or_create_context()`：优先从池中获取共享引擎，跳过重初始化
- 修改 `prewarm_services()`：预热后不再 close()，转为填充 ServicePool
- 每个会话只创建自己的 VAD 引擎和 Memory 系统
- `ServiceContext.load_cache()` 已有但未被使用，接入完整流程

## Capabilities

### New Capabilities
- `service-pool`: 服务实例池，全局共享无状态引擎，每个会话只创建有状态组件

## Impact

- 新增文件：`src/anima/core/service_pool.py`（~50 行）
- 修改文件：`session.py` 使用池、`websocket.py` prewarm 改为填充池
- 无破坏性变更，pool 不可用时自动降级为完整初始化
