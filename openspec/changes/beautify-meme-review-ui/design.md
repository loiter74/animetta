## Context

梗筛选面板（MemeReview.vue + MemeCard.vue）功能已完整，但视觉上停留在"能用"级别：纯 `bg-c-bg` 背景、flat 按钮、无装饰元素。而项目已有成熟的设计语言——glassmorphism 面板（InteractivePanel.vue）、霓虹发光（TitleBar.vue 状态点）、渐变进度条（ChatPanel.vue）、角落光晕动画（SceneEffects.vue）——这些都没有被应用到梗筛选面板上。

项目使用 UnoCSS 主题系统，所有需要的 color token 和 shortcut（`glass`、`glass-strong`、`gradient-accent`、`btn-accent` 等）均已存在。

## Goals / Non-Goals

**Goals:**
- 将 MemeReview 面板从 `bg-c-bg` flat 样式升级为 `glass-strong` 毛玻璃，与 InteractivePanel 视觉一致
- 升级 MemeCard 卡片样式：使用 `bg-c-card/50`、状态感知发光边框、hover 反馈
- 投票按钮对齐项目统一风格：好梗=xsuccess 绿、烂梗=xerror 红、active:scale-95 微动效
- 添加装饰层：渐变分割线、入场/出场过渡动效、投票反馈动画
- 完全使用现有 UnoCSS theme tokens，零新增依赖
- 保留所有现有功能逻辑（Socket 事件、store、路由结构）

**Non-Goals:**
- 不修改任何后端代码或 Socket 事件
- 不修改 store/memeReview.ts 的业务逻辑
- 不新增 npm 依赖或第三方库
- B站来源视觉化（已搁置）
- 不重构组件结构（不提取新子组件）

## Decisions

**Decision 1: 直接修改 MemeReview.vue + MemeCard.vue，而非新建组件**
- MemeReview 是专用面板，没有被其他地方复用，原地修改风险最低
- 如果后续需要复用到其他页面，再提取公共组件

**Decision 2: 面板使用 glass-strong + m-3 + rounded-2xl，复用 InteractivePanel 模式**
- `glass-strong` = `bg-c-surface/85 backdrop-blur-2xl border border-c-border rounded-2xl`
- InteractivePanel（设置面板）使用这个模式，梗筛选作为"右侧滑出面板"与之完全一致
- 取消 `border-l`（glass-strong 自带 border），加入 `m-3` 留边距

**Decision 3: 投票按钮使用 bg-c-success/15 / bg-c-error/15 + border + glow hover**
- 虽然项目统一模式是 `bg-c-accent/15 text-c-accent`，但好/烂有明确的正/负语义，使用绿/红更直观
- 与项目中 ModelLoadingOverlay 的状态色用法一致（success=green, error=red）
- 好梗 hover: `shadow-[0_0_8px_rgba(74,222,128,0.3)]`
- 烂梗 hover: `shadow-[0_0_8px_rgba(248,113,113,0.3)]`

**Decision 4: 动效使用 frontend-design skill 实现**
- 涉及多个动效：卡片切换、投票反馈、进度更新、入场动画
- frontend-design skill 专门处理高冲击力前端视觉，比手写更高效

## Risks / Trade-offs

- **[Low] glass-strong 改变面板尺寸**：当前面板 `w-full max-w-[440px]` 加 `m-3` 后实际内容宽度减少 12px。不影响功能，视觉上与其他面板一致。
- **[Low] Transition 动画冲突**：现有自定义 `panel-*` transition 需替换为项目标准 `animate-slide-in-right`。测试确认没有闪烁或断裂。
- **[Low] 主题一致性**：使用 `c-success`/`c-error` 好/烂配色而非 `c-accent`，与其他面板的"确认/取消"按钮配色一致，不会破坏视觉统一。
