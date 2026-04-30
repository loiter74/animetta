## ADDED Requirements

### Requirement: 装饰粒子效果
系统 SHALL 提供 `<SceneEffects>` 组件，在 Live2D 场景上叠加装饰性粒子动画，使用纯 CSS/SVG 实现。

#### Scenario: 粒子飘落动画
- **WHEN** SceneEffects 组件挂载
- **THEN** 显示 15-30 个半透明粒子（圆形光点），以不同速度从上往下缓慢飘落，带有左右轻微摇摆

#### Scenario: 粒子视觉风格
- **WHEN** 粒子渲染时
- **THEN** 粒子使用 accent 色系（粉紫色），大小 2-6px，透明度 0.2-0.6，带微弱发光效果

### Requirement: 角落光晕效果
SceneEffects SHALL 在视口角落渲染渐变光晕效果，增强二次元氛围。

#### Scenario: 角落光晕渲染
- **WHEN** SceneEffects 组件挂载
- **THEN** 在视口的左下角和右上角显示 accent 色系的径向渐变光晕，半径约 300px，透明度 0.05-0.1

### Requirement: z-index 层级
SceneEffects 的 z-index SHALL 介于 Live2D canvas 和 InteractivePanel 之间。

#### Scenario: 不遮挡交互面板
- **WHEN** SceneEffects 渲染时
- **THEN** 效果层位于 Live2D 之上、InteractivePanel 之下，不影响面板交互
