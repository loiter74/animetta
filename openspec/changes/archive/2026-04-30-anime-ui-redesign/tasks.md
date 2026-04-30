## 1. 主题系统扩展

- [x] 1.1 在 `uno.config.ts` 中新增渐变色 token（`gradient-accent`）和光效色 token（`c-glow`）
- [x] 1.2 在 `uno.config.ts` shortcuts 中新增 `animate-slide-in-right`、`animate-slide-out-right` 动画快捷类
- [x] 1.3 在 `animations.css` 中新增粒子飘落 keyframe（`fall`）和角落光晕 keyframe（`glowBreath`）

## 2. 布局重构（Phase 1: 全屏 Live2D + 浮动面板）

- [x] 2.1 重写 `AppLayout.vue`：移除 50/50 分割，Live2D 渲染器设为全屏背景层
- [x] 2.2 创建 `InteractivePanel.vue` 组件：绝对定位右侧浮动面板，支持展开/折叠动画
- [x] 2.3 在 InteractivePanel 内实现 Tab 导航（聊天/设置），带淡入淡出切换
- [x] 2.4 实现面板折叠按钮：折叠时显示窄条触发按钮，展开时面板滑入
- [x] 2.5 修复 `Live2DRenderer.vue` 默认模型路径（确保使用 `live2d/haru/haru_greeter_t03.model3.json`）

## 3. Live2D 交互增强

- [x] 3.1 在 `Live2DRenderer.vue` 添加鼠标跟随交互：监听 mousemove，调用 `model.focus(x, y)`
- [x] 3.2 优化 Live2D 模型在全屏模式下的缩放和居中策略

## 4. 聊天面板适配（Phase 2）

- [x] 4.1 改造 `ChatPanel.vue`：适配 InteractivePanel 的窄宽度（380px），移除独立面板外边距
- [x] 4.2 创建 `WelcomeScreen.vue`：消息列表为空时显示欢迎界面（角色名 + 问候语 + 提示）
- [x] 4.3 在 `MessageList.vue` 中集成 WelcomeScreen，消息到来后淡出欢迎界面
- [x] 4.4 优化 `MessageBubble.vue` 流式文本：新字符淡入效果
- [x] 4.5 中文化所有 UI 文案：InputBar 占位符改为 "输入消息..."，MessageList 空状态改为中文

## 5. 视觉增强（Phase 3）

- [x] 5.1 创建 `SceneEffects.vue`：CSS 粒子飘落效果（15-30 个光点，accent 色系）
- [x] 5.2 在 SceneEffects 中添加角落光晕渐变（径向渐变，accent 色）
- [x] 5.3 在 `AppLayout.vue` 中集成 SceneEffects（z-index 介于 Live2D 和面板之间）
- [x] 5.4 优化 `TitleBar.vue`：加深毛玻璃效果，添加底部 accent 色微光边框
- [x] 5.5 优化 `SpeakingIndicator.vue` 和 `TypingIndicator.vue` 样式适配浮动面板

## 6. 设置面板（Phase 4）

- [x] 6.1 创建设置面板内容组件：展示当前 ASR/TTS/LLM/VAD 服务名称
- [x] 6.2 添加 Live2D 模型信息展示（当前模型名 + 加载状态）
- [x] 6.3 添加 Persona 信息展示
- [x] 6.4 通过 `window.electronAPI?.getConfig` 获取后端配置并展示

## 7. PopOut 功能适配

- [x] 7.1 适配 `PopOutButton.vue` 到全屏 Live2D 场景（绝对定位在场景角落）
- [x] 7.2 弹出 Live2D 后，InteractivePanel 扩展到全宽（无 Live2D 场景时的备用布局）
