## ADDED Requirements

### Requirement: 全屏 Live2D 场景布局
系统 SHALL 将 Live2D 渲染器设为全屏尺寸（100vw × 100vh），作为应用的视觉背景层。所有 UI 面板以绝对定位叠加在场景之上。

#### Scenario: 应用启动布局
- **WHEN** 应用启动完成
- **THEN** Live2D canvas 占满整个视口（标题栏下方），交互面板浮动在右侧

#### Scenario: 窗口大小调整
- **WHEN** 用户拖拽窗口边缘调整大小
- **THEN** Live2D canvas 自适应新尺寸，交互面板保持相对位置不变

### Requirement: InteractivePanel 浮动交互面板
系统 SHALL 提供 `<InteractivePanel>` 组件，绝对定位在视口右侧，包含聊天和功能区域。面板 SHALL 使用 glassmorphism 半透明样式。

#### Scenario: 面板默认展开
- **WHEN** 应用启动
- **THEN** InteractivePanel 展开显示在视口右侧，宽度 380px，高度为视口高度减去标题栏

#### Scenario: 面板折叠
- **WHEN** 用户点击折叠按钮
- **THEN** InteractivePanel 滑出隐藏，只显示一个窄条触发按钮（48px 宽）

#### Scenario: 面板展开
- **WHEN** 面板处于折叠状态，用户点击触发按钮
- **THEN** InteractivePanel 滑入展开，带 300ms 过渡动画

### Requirement: 交互面板内 Tab 导航
InteractivePanel 内部 SHALL 提供顶部 Tab 切换，包含"聊天"和"设置"两个标签页。

#### Scenario: Tab 切换
- **WHEN** 用户点击"设置"标签
- **THEN** 面板内容从聊天视图切换到设置视图，带淡入淡出过渡

#### Scenario: 默认标签
- **WHEN** 面板首次渲染
- **THEN** 默认显示"聊天"标签页内容

### Requirement: 面板 z-index 层级
系统 SHALL 确保正确的 z-index 层级关系：Live2D canvas (z-0) < SceneEffects (z-10) < InteractivePanel (z-20) < SettingsOverlay (z-30) < TitleBar (z-40)。

#### Scenario: 面板不遮挡标题栏
- **WHEN** InteractivePanel 展开
- **THEN** 面板顶部位于标题栏下方，不遮挡标题栏区域
