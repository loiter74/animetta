## ADDED Requirements

### Requirement: 设置面板覆盖层
系统 SHALL 提供全屏半透明设置面板覆盖层 `<SettingsOverlay>`，以 glassmorphism 样式叠加在 Live2D 场景上方。

#### Scenario: 打开设置
- **WHEN** 用户点击面板内"设置"标签
- **THEN** 设置内容在 InteractivePanel 内部展示，背景变为更深的半透明遮罩

### Requirement: 配置状态展示
设置面板 SHALL 展示当前后端服务配置状态（只读展示），包括 ASR、TTS、LLM、VAD 的服务提供商名称。

#### Scenario: 显示当前服务配置
- **WHEN** 设置面板打开
- **THEN** 展示当前 ASR/TTS/LLM/VAD 服务提供商名称，以及连接状态

### Requirement: Live2D 模型信息
设置面板 SHALL 展示当前加载的 Live2D 模型名称和加载状态。

#### Scenario: 显示模型信息
- **WHEN** 设置面板打开
- **THEN** 展示当前 Live2D 模型文件名和加载状态（已加载/加载中/未加载）

### Requirement: Persona 信息展示
设置面板 SHALL 展示当前角色的 Persona 名称。

#### Scenario: 显示角色名称
- **WHEN** 设置面板打开
- **THEN** 展示当前 persona 配置名称（如 "neuro-vtuber"）
