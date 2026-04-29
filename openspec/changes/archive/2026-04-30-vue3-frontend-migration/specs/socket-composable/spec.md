## ADDED Requirements

### Requirement: Socket.IO 连接管理 Composable
系统 SHALL 提供 `useSocket` composable，管理 Socket.IO 连接生命周期（连接、断线重连、连接状态）。

#### Scenario: 连接后端
- **WHEN** 应用启动，`useSocket` 被调用
- **THEN** 自动连接到后端 `http://localhost:12394`，连接状态更新为 `connected`

#### Scenario: 断线自动重连
- **WHEN** 后端断开连接
- **THEN** Socket.IO 自动重连，状态显示 `reconnecting`，重连成功后恢复为 `connected`

#### Scenario: 手动断开
- **WHEN** 应用关闭
- **THEN** `useSocket` 调用 `socket.disconnect()` 清理连接

### Requirement: 连接状态 Store
系统 SHALL 提供 `connectionStore` (Pinia)，持有连接状态（connected/disconnecting/reconnecting）、后端 URL、延迟等信息。

#### Scenario: 状态栏显示连接状态
- **WHEN** 连接状态变化
- **THEN** `connectionStore.status` 更新，UI 状态栏自动响应显示对应颜色指示灯

### Requirement: 聊天业务 Composable
系统 SHALL 提供 `useChat` composable，封装聊天相关的 Socket.IO 事件（发送消息、接收回复、流式输出、中断）。

#### Scenario: 发送文本消息
- **WHEN** 调用 `useChat().sendText("你好")`
- **THEN** 通过 Socket.IO 发送 `text_input` 事件，消息追加到 chatStore

#### Scenario: 接收流式回复
- **WHEN** 后端发送 `text` 事件（流式 chunk）
- **THEN** chunk 追加到当前 assistant 消息，UI 实时更新

#### Scenario: 接收完整回复
- **WHEN** 后端发送 `control` 事件 signal 为 `conversation-end`
- **THEN** 当前 assistant 消息标记为完成，从流式状态转为最终状态

#### Scenario: 发送中断信号
- **WHEN** 用户点击中断按钮
- **THEN** 发送 `interrupt_signal` 事件到后端

### Requirement: 语音输入 Composable
系统 SHALL 提供 `useVoice` composable，管理麦克风录制、VAD 音量检测、音频数据发送。

#### Scenario: 开始录音
- **WHEN** 调用 `useVoice().startRecording()`
- **THEN** 获取麦克风权限，开始采集音频，通过 `raw_audio_data` 发送数据

#### Scenario: 音量指示
- **WHEN** 录音中麦克风检测到音量
- **THEN** composable 暴露 `volume` ref，UI 可绑定显示音量条

#### Scenario: 停止录音
- **WHEN** 调用 `useVoice().stopRecording()`
- **THEN** 发送 `mic_audio_end` 事件，停止采集

### Requirement: Socket 事件类型安全
所有 Socket.IO 事件 SHALL 有完整的 TypeScript 类型定义。

#### Scenario: 事件类型检查
- **WHEN** 开发者调用 `socket.emit('text_input', data)`
- **THEN** TypeScript 编译器检查 `data` 符合 `TextInputPayload` 类型定义
