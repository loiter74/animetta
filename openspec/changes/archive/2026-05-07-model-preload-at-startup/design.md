## Context

当前服务器启动流程 (`get_asgi_app()`)：
```
1. create_server(config) → WebSocketServer
2. asyncio.ensure_future(model_manager.warmup())   ← 空跑（无已注册模型）
3. asyncio.ensure_future(prewarm_services())        ← 调用不存在的 ServicePool → 静默失败
4. 返回 ASGI app
```

第一次语音输入时：
```
1. SessionManager 创建 ServiceContext
2. ServiceContext.init_asr() → FasterWhisperASR()
3. ASR Node 处理 → _get_model() → 下载/加载模型（~18s）
4. 期间 VAD 持续收到音频块 → 累积 process_audio 请求
5. 模型就绪后 → 请求雪崩 → 文件锁冲突
```

## Goals / Non-Goals

**Goals:**
- Faster-Whisper 模型在服务器启动时开始加载，用户首次语音输入时无需等待
- VAD、LLM、TTS 等模型的预加载也一并触发
- 热启动顺序与现有 `ModelLoadingManager` 架构一致

**Non-Goals:**
- 不改变 session 级别的模型隔离（每个 ServiceContext 仍创建自己的 engine 实例）
- 不引入新的配置项
- 不阻塞服务器启动（预加载异步进行）

## Decisions

**决策：用真正的模型注册替换不存在的 ServicePool 调用**

当前 `prewarm_services()`:
```python
from anima.core.service_pool import ServicePool  # ← 模块不存在
await ServicePool.init(self.config)
```

改为：
```python
async def prewarm_services(self) -> None:
    if self.config is None:
        return
    # 创建一次性的 ServiceContext 来触发引擎初始化
    from anima.core.service_context import ServiceContext
    from anima.config import AppConfig
    ctx = ServiceContext(session_id="__warmup__", model_manager=self.model_manager)
    await ctx.init_from_config(self.config)
    # 等待模型加载完成（不影响服务器启动）
    asyncio.ensure_future(self.model_manager.warmup())
```

`ServiceContext.init_from_config()` 会依次调用 `init_asr()`, `init_tts()`, `init_llm()`, `init_vad()`，每个方法创建引擎并调用 `model_manager.register(name, engine.preload, ...)`。之后 `model_manager.warmup()` 会并发执行所有已注册的 `preload()` 方法。

**不采用方案**：

- `model_manager.register()` 在启动阶段手动注册所有引擎的 loader 函数 → 需要知道具体引擎类型，耦合高
- 在 `get_asgi_app()` 中直接 `import` 并实例化模型 → 与现有架构不一致

## Risks / Trade-offs

- [低] `ServiceContext(session_id="__warmup__")` 会在内存中创建一次性的引擎实例和 ASR/TTS/LLM 客户端。约 0.5-2GB 额外内存（Faster-Whisper + Silero VAD）。 → 这是预期的，模型反正都要加载
- [低] 预热上下文不会被垃圾回收，直到整体重启 → 可接受，模型实例在所有会话间共享
- [忽略] 启动时间增加约 20s → 异步非阻塞，不影响 uvicorn 接受连接
