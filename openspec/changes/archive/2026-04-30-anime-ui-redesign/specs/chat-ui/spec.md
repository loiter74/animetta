## MODIFIED Requirements

### Requirement: ChatPanel 布局组件
系统 SHALL 提供 `<ChatPanel>` 组件作为浮动交互面板内的聊天区域。ChatPanel 不再是独立的全高面板，而是嵌入 InteractivePanel 内部的 Tab 页内容。

#### Scenario: 聊天面板渲染
- **WHEN** ChatPanel 组件挂载（在 InteractivePanel 内部）
- **THEN** 显示工具栏、消息列表、输入栏，整体风格适应浮动面板的窄宽度（380px）

#### Scenario: 空状态显示欢迎界面
- **WHEN** 消息列表为空
- **THEN** 显示 WelcomeScreen 欢迎界面，替代原来的简单空状态提示

## ADDED Requirements

### Requirement: 流式逐字动画
MessageBubble 的流式文本 SHALL 支持逐字淡入效果，新字符以轻微延迟逐个出现。

#### Scenario: AI 回复流式输出
- **WHEN** AI 消息处于 streaming 状态
- **THEN** 新文本字符以淡入效果出现，光标在最后一个字符位置闪烁

### Requirement: 中文化 UI 文案
所有用户可见的 UI 文案 SHALL 使用中文。

#### Scenario: 输入框占位符
- **WHEN** 输入框为空
- **THEN** 显示中文占位符 "输入消息..." 而非英文

#### Scenario: 空状态文案
- **WHEN** 显示空状态或欢迎界面
- **THEN** 所有文案使用中文
