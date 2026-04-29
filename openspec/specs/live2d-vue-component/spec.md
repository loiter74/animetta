## ADDED Requirements

### Requirement: Live2D 渲染组件
系统 SHALL 提供 `<Live2DRenderer>` Vue 3 组件，封装 pixi.js Application 和 pixi-live2d-display，接受 props 控制模型和表情。

#### Scenario: 模型加载
- **WHEN** 组件挂载并接收 `modelUrl` prop
- **THEN** 创建 pixi.js Application，加载 Live2D 模型，渲染到 canvas 元素，emit `model-loaded` 事件

#### Scenario: 模型加载失败
- **WHEN** 模型 URL 无效或网络错误
- **THEN** 组件 emit `model-error` 事件，显示占位状态（如可爱的加载失败提示）

### Requirement: 表情控制
`<Live2DRenderer>` SHALL 通过 prop 接受表情指令，驱动 Live2D 模型表情切换。

#### Scenario: 切换表情
- **WHEN** `expression` prop 变化为 `"happy"`
- **THEN** Live2D 模型执行 "happy" 表情动画，按表情策略控制持续时间和强度

### Requirement: 口型同步
`<Live2DRenderer>` SHALL 支持口型同步（viseme/lip sync），根据 TTS 音频数据驱动嘴部参数。

#### Scenario: TTS 音频播放时口型同步
- **WHEN** 收到 `audio_with_expression` 事件包含音频和 viseme 数据
- **THEN** Live2D 模型嘴部参数随音频数据实时变化

### Requirement: 自动行为
`<Live2DRenderer>` SHALL 支持自动眨眼、自动注视鼠标、空闲眼球运动等自然行为。

#### Scenario: 自动眨眼
- **WHEN** Live2D 模型处于空闲状态
- **THEN** 模型以随机间隔执行眨眼动画

#### Scenario: 鼠标注视跟踪
- **WHEN** 用户在 Live2D 渲染区域内移动鼠标
- **THEN** 模型眼球跟随鼠标位置

### Requirement: 响应式缩放
`<Live2DRenderer>` SHALL 自动适应容器大小变化，保持模型在容器内居中且比例正确。

#### Scenario: 容器大小变化
- **WHEN** 窗口大小改变或弹出/回收 Live2D
- **THEN** pixi.js renderer 自适应新尺寸，模型按比例缩放，保持居中
