## Context

Anima 当前 TTS 使用 `EdgeTTS`（通过 SSML prosody 调节 rate/pitch），提供 `edge_neurosama` 等 preset。现有架构通过 `ProviderRegistry` 插件机制注册 TTS provider，新的 provider 只需：
1. 创建 config 类（`@ProviderRegistry.register("tts", "kokoro")`）
2. 创建 service 类（`@ProviderRegistry.register_service("tts", "kokoro")` + `from_config()`）
3. 在 `TTSFactory._build_config()` 中添加 `kokoro` 分支
4. 在 `services.yaml` 中添加配置

Kokoro (hexgrad/Kokoro-82M) 是基于 StyleTTS2 架构的开源 TTS 模型，82M 参数，支持中英文，支持 8 种中文声线。其 v1.1-zh 版本新增了 100 个中文说话人数据。

## Goals / Non-Goals

**Goals:**
- 新增 Kokoro TTS provider，支持中文语音合成
- 新增 SoX 音频效果器管线，对合成后音频应用 GLaDOS 风格电子效果
- 所有新增代码遵循现有 ProviderRegistry 插件模式，不修改现有 TTS 实现
- Kokoro 推理在 CPU 上可用（82M 参数，无需 GPU）

**Non-Goals:**
- 不修改 output_node.py 或其他现有 graph 节点
- 不修改前端音频播放代码
- 不修改其他 TTS provider（Edge、GLM、OpenAI、ChatTTS 等）
- 不做声音克隆或自定义训练

## Decisions

### 1. Kokoro 作为 TTS 引擎

**选择**：Kokoro-82M v1.1-zh

**理由**：
- dnhkng/GLaDOS（5505 stars）等成熟项目已验证 Kokoro 可用于角色声音
- 82M 参数，CPU 推理单句 100-300ms，满足实时对话需求
- v1.1-zh 明确支持中文，8 种中文声线可选
- 开源 MIT 协议，可本地部署，无 API 调用成本

**备选**：使用 Edge TTS + SoX 效果器（选项 A）— 优点是零新增模型，但 Edge TTS 音质不够细腻，且受微软 API 限流影响。Kokoro 本地推理更稳定可控。

### 2. SoX 作为音频效果引擎

**选择**：`torchaudio.sox_effects` Python API

**理由**：
- SoX 效果器种类远超 pydub（chorus/flanger/bandpass/overdrive/compand 等）
- torchaudio 提供了 `apply_effects_file` 等 Python API，无需调用 CLI 子进程
- 效果链约 50ms 延迟，可忽略不计
- pydub 没有 chorus、overdrive、bandpass 等 GLaDOS 所需的关键效果

**备选**：pydub — 效果器太少，无法实现 chorus 等电子质感效果。FFmpeg — filter 语法复杂，不如 SoX 直观。

### 3. 效果器集成方式

**选择**：效果器内嵌在 `KokoroTTS.synthesize()` 内部，返回已处理音频

**理由**：
- 对上游和下游完全透明：output_node.py 不改一行代码
- 效果器可开关配置（`glados_effect.enabled: true/false`）
- 不生效时 Kokoro TTS 就是标准中文 TTS，可服务于其他场景

**备选**：作为独立的 graph node 插入 tts_node 和 output_node 之间 — 优点是可应用于任何 TTS provider，但当前需求只需针对 Kokoro，内嵌更简单。

### 4. Kokoro 声线选择

**选择**：`zf_xiaobei`（小北，女声）作为 GLaDOS 效果基座

**理由**：`zf_xiaobei` 是 Kokoro v1.1-zh 中最自然的中文女声，音色偏清冷，适合作为电子效果的基础。可通过 SoX pitch shift 进一步压低。

### 5. GLaDOS 效果链

```
Kokoro 合成 WAV → pitch -300 (降低音高，更低沉)
                 → stretch 1.05 (慢条斯理)
                 → overdrive 20 (过载失真)
                 → chorus 0.7 0.9 55 0.4 / 0.25 2 -t (电子共振)
                 → bandpass 300 3 (去除自然温暖感)
                 → compand 0.3,1 6:-70,-60,-20 -5 -90 0.2 (压限)
                 → gain -3 (输出电平)
```

参数基于 Stack Overflow SoX 机器人声方案（`overdrive + echo + synth sine fmod`）+ GLaDOS 风格调优。所有参数在 `services.yaml` 中可调。

## Risks / Trade-offs

- **[模型下载]** Kokoro 模型约 300MB，首次使用时需自动下载。Kokoro 本身无模型托管，需要通过 HuggingFace 或额外脚本下载 `kokoro-v1_1-zh.pth`。可利用 Anima 已有的 `E:/anima_data/models/` 目录缓存
- **[SoX 依赖]** torchaudio.sox_effects 需要系统安装 libsox。Windows 用户需额外配置。可在错误时给出清晰的安装指导
- **[效果品控]** GLaDOS 效果参数是经验值，可能需要微调。所有参数在配置层开放，无需改代码即可调参
- **[CPU 性能]** Kokoro 82M 在 CPU 上推理约 100-300ms/句，加上 SoX 50ms，总延迟约 150-350ms。如果过长，可考虑 ONNX 优化或使用 GPU
- **[中文发音质量]** Kokoro 的中文发音质量优于 Edge TTS，但不如 ChatTTS（专门为对话设计）。考虑到 GLaDOS 效果本身会改变声音特征，差异可接受
