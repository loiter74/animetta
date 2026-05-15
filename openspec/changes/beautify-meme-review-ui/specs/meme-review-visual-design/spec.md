## ADDED Requirements

### Requirement: 面板使用毛玻璃容器
梗筛选面板 SHALL 使用 `glass-strong` 毛玻璃样式，与项目设置面板视觉一致。

#### Scenario: 面板毛玻璃化
- **WHEN** 梗筛选面板打开
- **THEN** 面板 SHALL 使用 `bg-c-surface/85 backdrop-blur-2xl border border-c-border rounded-2xl` 样式
- **AND** 面板 SHALL 有 `m-3` 边距，与 InteractivePanel 对齐

#### Scenario: 面板入场动画
- **WHEN** 梗筛选面板从右则滑入
- **THEN** 面板 SHALL 使用 `animate-slide-in-right` 动画
- **AND** 背景遮罩层 SHALL 使用 `backdrop-blur-sm` 模糊效果

### Requirement: 投票按钮视觉系统
好/烂投票按钮 SHALL 使用项目的语义化配色系统。

#### Scenario: 好梗按钮
- **WHEN** 好梗按钮渲染
- **THEN** 按钮 SHALL 使用 `bg-c-success/15 text-c-success border border-c-success/20` 样式
- **AND** hover 时 SHALL 有 `shadow-[0_0_8px_rgba(74,222,128,0.3)]` 发光效果
- **AND** 点击时 SHALL 有 `active:scale-95` 缩放反馈

#### Scenario: 烂梗按钮
- **WHEN** 烂梗按钮渲染
- **THEN** 按钮 SHALL 使用 `bg-c-error/15 text-c-error border border-c-error/20` 样式
- **AND** hover 时 SHALL 有 `shadow-[0_0_8px_rgba(248,113,113,0.3)]` 发光效果
- **AND** 点击时 SHALL 有 `active:scale-95` 缩放反馈

### Requirement: 卡片过渡动效
梗卡片在切换时 SHALL 使用平滑的滑入/滑出动画。

#### Scenario: 切换动画
- **WHEN** 用户投票或点击跳过
- **THEN** 当前卡片 SHALL 以 `animate-slide-out-right` 动画离开
- **AND** 下一张卡片 SHALL 以 `animate-slide-in-right` 动画入场
- **AND** 两张卡片动画 SHALL 有短暂重叠，创造流畅过渡

### Requirement: 装饰性视觉元素
面板 SHALL 包含轻微装饰元素增强视觉层次。

#### Scenario: 渐变分割线
- **WHEN** 面板头部渲染
- **THEN** 头部底部 SHALL 有一条 `bg-gradient-to-r from-transparent via-c-accent/20 to-transparent` 渐变分割线

#### Scenario: 进度条渐变
- **WHEN** 进度条渲染
- **THEN** 进度条填充 SHALL 使用 `gradient-accent`（`bg-gradient-to-br from-c-accent to-c-accent-hover`）渐变
