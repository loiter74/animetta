## ADDED Requirements

### Requirement: VibeVoice TTS 提供者注册
系统 SHALL 注册 `vibe_voice` 为 TTS 提供者，允许在 `config/config.yaml` 中 `services.tts: vibe_voice` 切换。
系统 SHALL 通过 `@ProviderRegistry.register("tts", "vibe_voice")` 注册配置类 `VibeVoiceTTSConfig`。
系统 SHALL 通过 `@ProviderRegistry.register_service("tts", "vibe_voice")` 注册服务类 `VibeVoiceTTS`。

#### Scenario: 配置类型自动识别
- **WHEN** `config/services.yaml` 中 `tts.vibe_voice.type` 为 `"vibe_voice"`
- **THEN** Pydantic discriminated union SHALL 正确实例化为 `VibeVoiceTTSConfig`

#### Scenario: 服务类注册成功
- **WHEN** `ProviderRegistry.get_service_class("tts", "vibe_voice")` 被调用
- **THEN** SHALL 返回 `VibeVoiceTTS` 类

### Requirement: Remote 模式语音合成
`VibeVoiceTTS` 在 `mode="remote"` 时 SHALL 通过 HTTP API 调用远程 VibeVoice 服务。
系统 SHALL 使用 `httpx.AsyncClient` 发送 POST 请求到 `base_url` + `/tts`。
请求参数 SHALL 包含 `text`、`voice`、`language`、`num_speakers`。
响应 SHALL 返回 `audio/wav` 格式的二进制音频数据。
系统 SHALL 支持 `output_path` 参数：指定则保存到文件并返回路径，未指定则返回 `bytes`。

#### Scenario: Remote 模式 — 合成成功
- **WHEN** 调用 `synthesize("你好，世界", output_path=None)`
- **THEN** 返回 `bytes` 类型 WAV 音频数据，状态码 200

#### Scenario: Remote 模式 — 保存到文件
- **WHEN** 调用 `synthesize("你好", output_path="/tmp/out.wav")`
- **THEN** 文件 `/tmp/out.wav` SHALL 存在且为非空 WAV 文件，返回路径字符串

#### Scenario: Remote 模式 — 网络异常
- **WHEN** VibeVoice 服务不可达
- **THEN** SHALL 抛出 `ConnectionError` 并记录日志

### Requirement: Local 模式语音合成
`VibeVoiceTTS` 在 `mode="local"` 时 SHALL 通过子进程或本地进程调用 VibeVoice 模型进行推理。
系统 SHALL 支持配置 `model_size`（"1.5b" / "7b"）、`model_path`、`device`（"cuda:0"等）。
系统 SHALL 支持 VibeVoice 多说话人（1-4 speaker）合成。
本地推理 SHALL 输出 WAV 格式音频，不低于 16kHz 采样率。

#### Scenario: Local 模式 — 合成成功
- **WHEN** 调用 `synthesize("今天天气真好", voice="speaker_0")`
- **THEN** SHALL 返回有效的 WAV 音频字节数据，内容清晰可辨

#### Scenario: Local 模式 — 多说话人合成
- **WHEN** 调用 `synthesize("A:你好 B:你好呀", num_speakers=2)`
- **THEN** SHALL 返回包含两个不同 speaker 的对话音频

#### Scenario: Local 模式 — GPU 不可用
- **WHEN** `device="cuda:0"` 但 CUDA 不可用
- **THEN** SHALL 回退到 CPU 或抛出清晰的错误提示

### Requirement: TTSFactory 集成
`TTSFactory.create()` SHALL 支持 `provider="vibe_voice"`。
`TTSFactory.get_available_providers()` SHALL 返回中包含 `"vibe_voice"`。
`VibeVoiceTTS` SHALL 实现 `from_config` 类方法以支持 `ProviderRegistry.create_service()` 路径。

#### Scenario: 工厂创建实例
- **WHEN** `TTSFactory.create(provider="vibe_voice", mode="remote", base_url="http://localhost:8765")`
- **THEN** SHALL 返回 `VibeVoiceTTS` 实例且 `mode` 为 `"remote"`

### Requirement: 配置可切换
用户 SHALL 通过 `config/config.yaml` 的 `services.tts` 字段在 Edge/GLM/VibeVoice 等 TTS 提供者间切换。
`VibeVoiceTTS` SHALL 在初始化时从 `VibeVoiceTTSConfig` 读取参数。
`VibeVoiceTTS.synthesize()` SHALL 实现 `TTSInterface` 接口的完整语义。

#### Scenario: 从 Edge 切换到 VibeVoice
- **WHEN** `config.yaml` 中 `services.tts` 从 `"edge"` 改为 `"vibe_voice"`
- **THEN** `ServiceContext.init_tts()` SHALL 创建 `VibeVoiceTTS` 而非 `EdgeTTS`
