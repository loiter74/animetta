## ADDED Requirements

### Requirement: VAD 服务注册成功
导入 VAD 模块后，silero 和 mock 两个 VAD 服务必须在 ProviderRegistry 中注册成功。

#### Scenario: VAD 模块导入后注册
- **WHEN** `from anima.services.intelligence.vad import VADFactory` 执行
- **THEN** `ProviderRegistry.list_services('vad')` 返回包含 `['silero', 'mock']`

### Requirement: VAD 工厂降级到 MockVAD
当 VAD 主创建失败时，工厂必须降级到 MockVAD 而不是抛出 ModuleNotFoundError。

#### Scenario: VAD 创建失败自动降级
- **WHEN** `VADFactory.create_from_config(config)` 主创建失败
- **THEN** 返回 MockVAD 实例，不抛出 `ModuleNotFoundError`

### Requirement: LLM 工厂降级到 MockLLM
当 LLM 主创建失败时，工厂必须降级到 MockLLM 而不是抛出 ModuleNotFoundError。

#### Scenario: LLM 创建失败自动降级
- **WHEN** `LLMFactory.create_from_config(config)` 主创建失败
- **THEN** 返回 MockLLM 实例，不抛出 `ModuleNotFoundError`

### Requirement: output_node 发送 expression 事件
output_node 必须读取 emotion 状态并通过 Socket.IO 发送 expression 事件。

#### Scenario: 有 emotion 时发送表情
- **WHEN** `state["emotion"]` 为非空字符串（如 "happy"）
- **THEN** `sio.emit` 被调用，事件名包含 expression 相关事件，payload 包含该 emotion 值

### Requirement: output_node 发送带 volumes 的音频
output_node 必须在 audio_with_expression 事件中包含 volumes 数组用于口型同步。

#### Scenario: TTS 返回文件路径时计算 volumes
- **WHEN** `state["tts_audio"]` 为一个存在的音频文件路径
- **THEN** `audio_with_expression` 事件的 payload 包含 `volumes` 字段（List[float]）

### Requirement: output_node 发送 conversation-end 控制信号
output_node 必须在输出完成后发送 control 信号告知前端对话结束。

#### Scenario: 输出完成后发送结束信号
- **WHEN** output_node 完成文本和音频的推送
- **THEN** `sio.emit("control", {"signal": "conversation-end"})` 被调用
