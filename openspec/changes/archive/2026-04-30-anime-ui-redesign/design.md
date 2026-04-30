## Context

当前 Anima 前端采用简单的 50/50 水平分割布局：左半屏 Live2D、右半屏聊天面板。这种布局存在以下问题：

1. **空间利用低效** — Live2D 模型只占半个屏幕，视觉冲击力不足
2. **视觉层次扁平** — 没有叠加/层级关系，两个面板"各管各的"
3. **缺少装饰层** — 没有粒子、光效、渐变等二次元常见装饰元素
4. **功能缺失** — 无设置面板、无引导页、模型路径错误

参考 AIRI 项目的核心设计决策：**全屏 Live2D 场景 + 绝对定位浮动交互面板**。角色是视觉中心，所有 UI 元素以半透明叠加形式浮动在场景之上。

### 现有技术栈
- Vue 3 + TypeScript + UnoCSS（已就位）
- electron-vite 构建系统
- pixi.js + pixi-live2d-display（Live2D 渲染）
- Pinia 状态管理
- Socket.IO 客户端通信

## Goals / Non-Goals

**Goals:**
- 全屏 Live2D 角色展示，作为应用视觉中心
- 浮动交互面板（聊天 + 功能）叠加在 Live2D 场景上
- Glassmorphism 半透明 UI 组件
- 装饰层（粒子、光晕）增强二次元氛围
- 设置面板覆盖层（配置模型、服务等）
- 面试展示级视觉品质
- 代码结构清晰，便于面试官理解

**Non-Goals:**
- 不引入新的 UI 框架（如 Element Plus、Naive UI）
- 不做移动端适配（仅桌面 Electron）
- 不做浅色主题（保持暗色二次元风格）
- 不修改后端 API 或 WebSocket 协议
- 不做插件/扩展系统（仅内置功能）

## Decisions

### D1: 全屏 Live2D + 浮动面板布局（AIRI 模式）

**选择**: Live2D 渲染占满整个视口，交互面板以绝对定位浮动在右侧。

**替代方案**: 保持 50/50 分割，增加装饰
- 优点：实现简单，改动小
- 缺点：视觉冲击力不足，与 AIRI 差距大

**布局结构**:
```
┌──────────────────────────────────────────┐
│ TitleBar (毛玻璃)                         │
├──────────────────────────────────────────┤
│                                          │
│  Live2D Scene (100% width × 100% height) │
│                                          │
│          ┌─────────────┐                 │
│          │ Interactive │                 │
│          │   Panel     │                 │
│          │  (聊天+功能) │                 │
│          │  浮动右侧    │                 │
│          │  可折叠     │                  │
│          └─────────────┘                 │
│                                          │
└──────────────────────────────────────────┘
```

InteractivePanel 属性:
- 绝对定位 `right: 16px, top: 标题栏底部, height: calc(100vh - 标题栏 - 间距)`
- 最大宽度 420px，最小宽度 320px
- 毛玻璃背景 `bg-$c-surface/60 backdrop-blur-2xl`
- 可通过侧边按钮折叠/展开
- 内部分为: 聊天区（默认）+ 功能区（Tab 切换）

### D2: 交互面板内 Tab 式导航

**选择**: InteractivePanel 内部使用顶部 Tab 切换聊天/功能视图。

Tab 页面:
1. **聊天** (默认) — MessageList + InputBar + 工具栏
2. **设置** — 模型选择、服务配置、Persona 配置（只读展示当前状态）

**替代方案**: 侧边栏图标导航
- 缺点：宽度不够，图标导航在小面板内拥挤

### D3: 装饰层组件 SceneEffects

**选择**: 独立的 `<SceneEffects>` 组件，渲染在 Live2D canvas 和 UI 面板之间（z-index 层级: canvas < effects < panels）。

装饰元素:
- 缓慢飘落的粒子（樱花/星星/光点）
- 角落光晕渐变（accent 色系）
- 可选的网格背景纹理

使用纯 CSS/SVG 实现，不用 Canvas（避免与 pixi.js 冲突）。

### D4: 欢迎界面 WelcomeScreen

**选择**: 当消息列表为空时，InteractivePanel 的聊天区域显示欢迎界面。

内容:
- 角色名（从 persona 配置读取或默认 "Anima"）
- 一句欢迎语 + 快速操作按钮
- 简单的淡入动画

### D5: Live2D 鼠标跟随交互

**选择**: Live2D 模型添加鼠标位置追踪，模型眼睛/头部跟随鼠标方向。

实现: 在 Live2DRenderer 的 canvas 上监听 mousemove 事件，将坐标映射到模型参数。pixi-live2d-display 内置支持 `model.focus(x, y)` 方法。

### D6: 无新依赖

**选择**: 不引入新的 npm 包。所有 UI 效果使用 Vue 3 + UnoCSS + 原生 CSS 动画实现。

## Risks / Trade-offs

- **[性能] 粒子效果可能影响渲染帧率** → 使用 CSS `will-change: transform` 优化，粒子数量限制在 30 个以内，低端机可通过设置关闭
- **[复杂度] 全屏布局需要更多绝对定位** → 封装 InteractivePanel 为独立组件，内聚布局逻辑
- **[兼容性] backdrop-filter 在某些 Electron 版本有 bug** → Electron 33 (Chromium 130) 完全支持，无需 polyfill
- **[可维护性] 浮动面板的响应式** → 使用固定像素值 + min/max 约束，不做断点响应式（桌面专用）
- **[学习曲线] AIRI 模式对面试官来说可能不直观** → 交互面板折叠/展开状态清晰，设置面板提供全局视图

## Migration Plan

分 4 个阶段实施，每个阶段可独立验证：

1. **Phase 1: 布局重构** — AppLayout 重写为全屏 Live2D + 浮动面板，修复模型路径
2. **Phase 2: 聊天面板升级** — 聊天面板样式适配浮动面板，新增欢迎界面
3. **Phase 3: 视觉增强** — SceneEffects 装饰层，TitleBar 优化，动画补充
4. **Phase 4: 设置面板** — SettingsOverlay 覆盖层，展示当前配置状态

无数据库/后端变更，无需回滚策略。前端变更可通过 git revert 完整回滚。
