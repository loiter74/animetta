## Why

Anima 当前 TTS 声音缺乏角色辨识度。Edge TTS 的 `edge_neurosama` preset 只能做简单的语速/音高调整（+25% rate, +120Hz pitch），效果像一个加速的"可爱电子音"，而非 Portal 2 中 GLaDOS 那种冷静、低沉、带电子合成质感的声音。Kokoro TTS 是 dnhkng/GLaDOS（⭐5505）等成熟项目选用的底层引擎，支持中文语音，配合 SoX 音频效果器可精确还原 GLaDOS 风格。

## What Changes

- **新增 Kokoro TTS Provider**：注册新的 TTS provider `kokoro`，支持中文语音合成（8种中文声线）
- **新增 GLaDOS 音频效果器**：基于 SoX 的音频后处理管线，对合成后的音频应用 pitch shift、chorus、bandpass、overdrive 等效果，产生电子合成质感
- **新增 `kokoro_glados` 配置预设**：在 `services.yaml` 中添加一键启用配置
- **新增依赖**：`kokoro`（TTS 模型）、`sox`（音频效果器）
- **无任何既有代码修改**：通过 ProviderRegistry 插件机制新增，不修改现有 TTS 实现

## Capabilities

### New Capabilities
- `kokoro-tts-provider`: Kokoro TTS 引擎集成，支持中文语音合成（8种中文声线），82M 参数模型，CPU 可运行
- `glados-audio-effects`: SoX 音频效果管线，对 TTS 输出应用 chorus/pitch shift/bandpass/overdrive/compand 效果链，产生 GLaDOS 风格电子合成声

### Modified Capabilities
- （无 — 纯新增，不改现有能力）

## Impact

- **新增依赖**：`kokoro` >= 0.19（HuggingFace 模型）、`sox` 命令行工具（系统级）、`torchaudio`（用于 SoX 效果器 Python API）
- **配置**：`config/services.yaml` 新增 `kokoro_glados` 预设，`config/config.yaml` 可将 `services.tts` 切换为 `kokoro_glados`
- **服务注册**：`ProviderRegistry` 新增 `kokoro` provider 类型（config + service 注册）
- **模型存储**：Kokoro 82M 模型首次使用时自动下载（~300MB），可缓存至 `E:/anima_data/models/kokoro/`
- **无运行时性能影响**：Kokoro 推理约 100-300ms/句，SoX 效果约 50ms，总延迟可接受
