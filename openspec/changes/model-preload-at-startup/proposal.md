## Why

Faster-Whisper ASR 模型（distil-large-v3）约 18s 的冷启动加载发生在**第一次语音输入时**而非服务器启动时，导致：

1. **VAD 空转风暴**：模型加载期间，VAD 不断收到音频块并误判为"说话结束"，堆积大量音频处理请求
2. **文件锁冲突**：堆积的请求尝试读取同一个临时 mp3 文件，触发 `WinError 32`（文件被占用）
3. **ASR Node 雪崩**：模型加载完成后，大量 ASR 请求同时触发，日志爆炸

## What Changes

- 修复 `prewarm_services()` 方法，使其在服务器启动时实际触发模型加载
- 不再调用已删除的 `ServicePool.init()`，改用直接创建临时的 `ServiceContext` 并调用各服务的 `preload()` 方法
- 确保 Faster-Whisper、TTS、VAD、LLM 等模型在第一个用户连接到达之前开始加载

## Capabilities

### New Capabilities
无

### Modified Capabilities
无

## Impact

- `src/anima/orchestration/server/websocket.py`：`prewarm_services()` 逻辑替换
- `src/anima/core/socketio_server.py`：可能调整 warmup 调用顺序
- ASR 首次请求延迟从 18s → 0s（模型已预加载）
