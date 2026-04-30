## ADDED Requirements

### Requirement: 渐变色扩展
系统 SHALL 在 UnoCSS 主题中新增渐变色 token，用于背景光晕、按钮渐变等场景。

#### Scenario: 渐变 token 使用
- **WHEN** 组件使用 `bg-gradient-accent` shortcut
- **THEN** 渲染为从 accent 色到 accent-hover 色的对角线渐变

### Requirement: 光效色 token
系统 SHALL 新增光效相关的颜色 token，用于粒子发光、面板边框发光等。

#### Scenario: 光效色使用
- **WHEN** 组件使用 `text-$c-glow` 或 `shadow-$c-glow` token
- **THEN** 渲染为 accent 色系的发光效果颜色 `rgba(232, 121, 168, 0.4)`

### Requirement: 扩展动画快捷类
系统 SHALL 在 UnoCSS shortcuts 中新增常用动画快捷类。

#### Scenario: 面板滑入动画
- **WHEN** 使用 `animate-slide-in-right` class
- **THEN** 元素从右侧滑入，300ms cubic-bezier(0.16, 1, 0.3, 1) 过渡

#### Scenario: 面板滑出动画
- **WHEN** 使用 `animate-slide-out-right` class
- **THEN** 元素向右侧滑出，250ms ease-in 过渡

### Requirement: 新增粒子飘落 keyframe
系统 SHALL 在 animations.css 中新增粒子飘落动画 keyframe。

#### Scenario: 粒子飘落
- **WHEN** 粒子元素使用 `animate-fall` class
- **THEN** 元素从上方飘落到下方（translateY 0 → 100vh），带轻微水平摇摆（translateX ±15px），15-25s 循环
