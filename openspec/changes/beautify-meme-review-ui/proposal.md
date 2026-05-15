## Why

梗筛选面板（MemeReview.vue + MemeCard.vue）目前功能完整但视觉简陋——纯色背景、flat 按钮、无发光/毛玻璃效果，与项目整体的二次元霓虹玻璃态主题严重不一致。这次改造让它在视觉上与 InteractivePanel、SettingsPanel 等其他面板对齐。

## What Changes

- **面板容器重写**：替换 `bg-c-bg` 纯色背景为 `glass-strong` 毛玻璃面板，对齐 InteractivePanel 模式
- **梗卡片升级**：从 `bg-c-surface` 升级为 `bg-c-card/50` + glow 边框 + 状态感知的彩色发光
- **按钮系统对齐**：好/烂按钮使用项目统一的 `bg-c-success/15` / `bg-c-error/15` 模式 + active 微动效
- **装饰氛围**：添加渐变装饰线、角落光晕呼吸动画、入场过渡动效
- **动效增强**：卡片切换动画、投票反馈动画、进度更新微交互动画
- 不改变现有功能逻辑、数据流、Socket 事件

## Capabilities

### New Capabilities

- `meme-review-visual-design`: 梗筛选面板的视觉设计系统——毛玻璃容器、卡片发光、按钮规范、装饰元素

### Modified Capabilities

- `meme-review-ui`: 现有规范中关于视觉表现的需求变更——卡片过渡动画（原 spec 第 39/45 行）、投票按钮样式、进度指示器视觉、空状态/完成状态视觉

## Impact

- **Files**: `frontend/src/views/MemeReview.vue`, `frontend/src/components/meme/MemeCard.vue`
- **Style**: 仅使用现有的 UnoCSS theme tokens，不新增依赖
- **No breaking changes**: 功能逻辑、API 调用、路由结构完全不变
