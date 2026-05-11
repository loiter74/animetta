## Why

字幕在 TTS 音频播完之前就消失了。当前 `useSubtitle.ts` 在收到完整文本后用硬编码 6 秒定时器隐藏字幕，而实际音频（尤其是 GPT-SoVITS 生成的长回复）可能持续 10-15 秒以上，导致用户看到字幕提前消失的体验断裂。

## What Changes

- **`frontend/src/composables/useSubtitle.ts`**: 不再依赖硬编码的 6 秒隐藏定时器
- 新增对 `audio_with_expression` 事件的监听，根据实际音频数据量估算播放时长，用真实时长驱动隐藏时机
- 保留 `stop_audio`（用户打断）和 `subtitle.translation` 事件对隐藏时机的覆盖逻辑
- 不修改后端，不修改音频播放层的 `useLive2D.ts`，纯前端改动

## Capabilities

### New Capabilities
- `subtitle-timing`: 字幕显示时长由音频实际播放时长驱动，而非固定超时。关键行为：字幕保持可见直到音频播放完毕（+ 短暂缓冲），而不是在文字到达后固定 N 秒消失。

### Modified Capabilities

无。现有能力的行为不发生变化，只是修复一个显示时机 bug。

## Impact

- `frontend/src/composables/useSubtitle.ts`: 新增 ~15 行代码（socket 监听 + 时长计算 + 动态隐藏调度）
- 零后端影响，零音频播放层影响
- 不影响聊天记录消息列表（`useChat.ts` 独立处理）
