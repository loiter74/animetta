## Why

Anima 当前的 TTS 方案（Edge TTS / GLM TTS / ChatTTS）在多说话人长对话合成方面存在明显短板：
- Edge TTS 只能单说话人、短文本
- GLM TTS 是远程 API，依赖网络且无法本地化
- ChatTTS 开源但模型能力有限，不支持多人对话

Microsoft VibeVoice 是开源 MIT 协议的 SOTA 长文本多说话人 TTS 模型，支持 90 分钟连续合成、4 个不同 speaker、中英双语。用户本地有 RTX 5090D（24GB+ VRAM），完全可以本地运行 VibeVoice 1.5B/7B 模型，获得高质量、低延迟、离线的语音合成能力。

## What Changes

- **新增 `vibe_voice` TTS 提供者** — 支持本地推理（通过 HuggingFace transformers 或 VibeVoice 官方推理脚本）和远程 API 两种部署模式
- **配置系统** — 新增 `VibeVoiceTTSConfig`，支持配置本地模型路径 / 远程 API 端点、speaker 数量、模型大小（1.5B / 7B）等参数
- **服务实现** — 实现 `VibeVoiceTTS(TTSInterface)`，支持本地 GPU 推理和 HTTP API 两种模式的 `synthesize()`
- **多说话人支持** — 利用 VibeVoice 的原生多 speaker 能力，为 Anima 的对话系统提供多人播客式语音合成
- **配置切换** — 用户可在 `config/config.yaml` 中 `services.tts: vibe_voice` 一键切换

## Capabilities

### New Capabilities

- `vibe-voice-tts`: VibeVoice TTS 提供者的配置、本地推理服务、远程 API 调用

### Modified Capabilities

- 无（新提供者，不影响现有 TTS 实现）

## Impact

- **新增依赖**: `torch`（如本地推理）、`transformers`、`httpx`（如 API 模式）
- **新增文件**: 1 个配置类 + 1 个服务实现类
- **修改文件**: TTS 配置 Union、工厂方法、服务导出、services.yaml
- **硬件要求**: 本地推理需 NVIDIA GPU（RTX 3090+/5090D），1.5B 模型 ~6GB VRAM，7B 模型 ~16GB VRAM
- **可选**: VibeVoice 模型权重下载（HuggingFace，~3-15GB）
