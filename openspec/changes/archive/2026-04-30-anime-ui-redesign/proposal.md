## Why

当前前端 UI 存在两个核心问题：

1. **视觉品质不足**：粗糙的 50/50 分割布局、缺少装饰元素、glassmorphism 主题色定义了但未充分利用，整体观感达不到展示级水平
2. **功能缺失**：无设置面板、无连接状态详细信息、Live2D 模型路径错误、输入框英文占位符、缺少欢迎界面和交互引导

这次改版参考 AIRI 项目的设计语言，目标是打造一个适合**面试官展示**的高品质二次元桌面应用 UI。

## What Changes

- **BREAKING**: 布局从 50/50 分割改为全屏 Live2D + 浮动聊天面板（AIRI 风格）
- 新增浮动式侧边栏交互面板（InteractiveArea），绝对定位覆盖在 Live2D 场景上
- 新增玻璃拟态（Glassmorphism）设置面板覆盖层
- 重设计聊天 UI：对话气泡动画、打字指示器优化、流式文本逐字淡入
- 修复 Live2D 模型默认路径（haru → 正确路径）
- 新增欢迎/空状态引导页面
- 新增粒子/光效背景装饰层
- 优化 TitleBar 视觉（毛玻璃 + 渐变边框）
- 中文化所有 UI 文案
- 新增连接状态指示器（悬浮气泡显示详细信息）

## Capabilities

### New Capabilities
- `interactive-panel`: 全屏 Live2D + 浮动交互面板布局系统（核心布局变更）
- `settings-overlay`: 玻璃拟态设置面板覆盖层
- `scene-effects`: 背景粒子、光效等装饰层系统
- `onboarding`: 欢迎/引导界面

### Modified Capabilities
- `anime-theme`: 扩展色板（渐变、光效色），新增动画快捷类，优化 glassmorphism shortcuts
- `chat-ui`: 气泡样式升级为浮动面板内嵌模式，新增流式逐字动画，中文化
- `live2d-vue-component`: 全屏显示模式，鼠标跟随交互，修复模型路径
- `window-manager`: 适配新布局的窗口尺寸策略

## Impact

- **前端组件**: AppLayout.vue 重写（核心变更），TitleBar.vue、ChatPanel.vue、MessageBubble.vue、InputBar.vue 样式大幅调整
- **新增组件**: InteractivePanel.vue、SettingsOverlay.vue、SceneEffects.vue、WelcomeScreen.vue
- **UnoCSS 配置**: uno.config.ts 新增动画 keyframes、渐变色、扩展 shortcuts
- **animations.css**: 新增粒子、流光、脉冲等动画
- **Live2D composable**: 支持鼠标跟随交互
- **无后端影响**: 纯前端变更，WebSocket 协议不变
