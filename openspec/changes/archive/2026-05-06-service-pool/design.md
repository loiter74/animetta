## Context

当前每个 `ServiceContext` 通过 `load_from_config()` 创建所有引擎。`prewarm_services()` 创建一个临时 context 后立即 `close()`，引擎被销毁。第二个 session 仍需完整重初始化 ~8s。

`ServiceContext` 已有 `load_cache()` 方法（line 88）接收外部引擎实例并跳过 init，但未被任何代码调用。

## Goals / Non-Goals

**Goals:**
- 全局共享 LLM/TTS/ASR 引擎实例，避免每个会话重复初始化
- 每个会话保持独立的 VAD 状态和 Memory 系统
- prewarm 填充池而非销毁引擎
- 池不可用时自动降级为完整初始化

**Non-Goals:**
- 不做连接池（httpx 已内置连接复用）
- 不做模型热加载（只管理生命周期）
- 不改动 ServiceContext 内部逻辑

## Decisions

### D1: ServicePool 实现

```python
class ServicePool:
    _llm: Optional[LLMInterface] = None
    _tts: Optional[TTSInterface] = None
    _asr: Optional[ASRInterface] = None
    _ready: bool = False

    @classmethod
    async def init(cls, config):
        ctx = ServiceContext()
        ctx.session_id = "__pool__"
        await ctx.load_from_config(config)
        cls._llm = ctx.llm_engine
        cls._tts = ctx.tts_engine
        cls._asr = ctx.asr_engine
        cls._ready = True
        # Don't close! Engines stay alive.

    @classmethod
    def get_context(cls) -> dict:
        return {
            "llm_engine": cls._llm,
            "tts_engine": cls._tts,
            "asr_engine": cls._asr,
        } if cls._ready else {}
```

### D2: SessionManager 使用池

`get_or_create_context()` 改为：
```python
async def get_or_create_context(self, sid, config, ...):
    if sid not in self.contexts:
        ctx = ServiceContext()
        ctx.session_id = sid
        ctx.send_text = websocket_send

        pool = ServicePool.get_context()
        if pool:
            ctx.load_cache(config=config, **pool)
            await ctx.init_vad(config.vad)
            await ctx.init_memory()
        else:
            await ctx.load_from_config(config)

        self.contexts[sid] = ctx
    return self.contexts[sid]
```

### D3: Prewarm 改为填充池

```python
async def prewarm_services(self):
    await ServicePool.init(self.config)
```

## Architecture

```
Server Start:
  prewarm_services()
    → ServicePool.init(config)
      → ctx = ServiceContext("__pool__")
      → load_from_config() → 引擎创建
      → 提取 llm/tts/asr 引用存入 Pool
      → ctx 不再 close()，引擎常驻内存

New Session N:
  get_or_create_context(sid)
    → ctx = ServiceContext()
    → if ServicePool.ready:
        ctx.load_cache(llm=pool.llm, ...)  ← 秒级
        ctx.init_vad()                      ← 轻量
        ctx.init_memory()                   ← 轻量
    → else:
        ctx.load_from_config(config)        ← 降级

Session close:
  ctx.close()
    → 只关 VAD + Memory
    → 不关 LLM/TTS/ASR（池管理）
```

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| LLM 引擎的 history 跨会话泄漏 | `llm_node.py` 每次调用传完整 messages，引擎的 history 不被流式路径使用 |
| 共享引擎 OTel tracing 串扰 | TracingProxy 使用 ContextVar，每个 async task 隔离 |
| 引擎崩溃影响所有会话 | 池检测到错误后创建新引擎 |
| pool 的 ctx 永不 close 导致资源泄漏 | 服务器关闭时 ServicePool.shutdown() 统一清理 |
