## Context

当前字幕隐藏逻辑在 `frontend/src/composables/useSubtitle.ts` 中：

1. 后端 `output_node.py` 在 TTS 合成之前就发送了 `sentence(is_complete=true)` 事件
2. 前端收到后调用 `scheduleHide(6000)`——6 秒硬编码倒计时
3. TTS 合成 + 音频播放实际耗时可能 > 6 秒（尤其 GPT-SoVITS 长回复）
4. `stop_audio` 事件只由用户中断触发，正常对话流程不发射
5. 音频播放层（`useLive2D.ts`）和字幕层（`useSubtitle.ts`）完全解耦，无通信机制

结果：字幕在音频还在播放时就消失了。

## Goals / Non-Goals

**Goals:**
- 字幕显示时长由实际音频播放时长驱动，不再用固定 6 秒
- 保留 `stop_audio`（用户打断时 1.5s 隐藏）和 `subtitle.translation`（重置 6s 计时器）的行为
- 纯前端改动，不动后端代码

**Non-Goals:**
- 不改变 `useLive2D.ts` 的音频播放逻辑
- 不引入新的跨模块通信机制（如事件总线、Pinia store 共享）
- 不修改后端减少 `output_node.py` 的 sentence/audio 发送时序（只是优化方向，非本变更范围）

## Decisions

### Decision 1: 在 `useSubtitle.ts` 中直接监听 `audio_with_expression` 事件

**选择**：`useSubtitle.ts` 通过 `getSocket()` 监听 `audio_with_expression` 事件，从音频数据量估算持续时间，动态设置隐藏计时器。

**为什么不是其他方案：**

| 方案 | 问题 |
|------|------|
| `useLive2D.ts` 的 `audio.onended` 通知 subtitle | 需要跨 composable 通信（事件总线 / provide-inject / Pinia），引入耦合 |
| 后端在 `audio_with_expression` 加 `duration` 字段 | 后端改动，需确认每个 TTS 实现是否提供时长信息 |
| 增大固定超时（如 15s） | 短音频场景白等太久，治标不治本 |

**选择理由**：自包含、零耦合、纯前端、严格局部化。`socket.on('audio_with_expression')` 和现有 `socket.on('sentence')` 在同一层级的同一个 composable 中处理，模式一致。

### Decision 2: 用 WAV 字节估算音频时长

当前 `audio_with_expression` 的 `format` 是 `wav`，WAV 头部包含采样率、通道数等信息。但前端直接解析 WAV 头部会增加复杂度。

**选择**：假设 24kHz 16bit mono（Kokoro 的标准输出格式），用 base64 解码后的字节数估算：

```
estimated_seconds = raw_bytes / (sample_rate * channels * bytes_per_sample)
                  = raw_bytes / (24000 * 1 * 2)
                  = raw_bytes / 48000
```

**估算偏差容忍**：GPT-SoVITS 可能输出不同采样率（16kHz 或 24kHz）。估算不准时+0.5s 安全缓冲，保证"音频播完前字幕不消失"。即使少算 1-2 秒，也比固定 6 秒好得多。

### Decision 3: 保留所有现有事件的处理逻辑

- `stop_audio` → 1.5s 后隐藏（用户打断时快速消失）
- `subtitle.translation` → 重置 6s 计时器（翻译可能更晚到达）
- `scheduleHide` 函数逻辑不变，只是传入的 delay 变成动态的

## Risks / Trade-offs

- **[精度风险]** 音频时长估算可能不够精确 → 加 +1s 安全缓冲保守处理
- **[边缘情况]** 音频数据为空或损坏 → 兜底用 3s 最小超时
- **[后端耦合]** 未来后端改了 `audio_with_expression` 格式（更换 format、移除 base64）→ 保持对 `data.audio_data` 的防御性访问
