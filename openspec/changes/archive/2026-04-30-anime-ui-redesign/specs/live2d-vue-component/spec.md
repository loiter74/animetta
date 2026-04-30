## MODIFIED Requirements

### Requirement: Live2D 渲染组件
系统 SHALL 提供 `<Live2DRenderer>` Vue 3 组件，封装 pixi.js Application 和 pixi-live2d-display。组件 SHALL 支持全屏渲染模式和鼠标跟随交互。

#### Scenario: 模型加载
- **WHEN** 组件挂载
- **THEN** 创建 pixi.js Application 填满父容器，加载 Live2D 模型，渲染到 canvas 元素，emit `model-loaded` 事件

#### Scenario: 全屏渲染
- **WHEN** Live2DRenderer 父容器为全屏尺寸
- **THEN** canvas 填满整个容器，模型居中显示并适当缩放

#### Scenario: 模型加载失败
- **WHEN** 模型 URL 无效或加载错误
- **THEN** 组件显示优雅的占位状态，不阻塞其他 UI 功能

### Requirement: 自动行为
`<Live2DRenderer>` SHALL 支持自动眨眼、鼠标位置追踪（模型眼睛/头部跟随鼠标方向）、空闲眼球运动等自然行为。

#### Scenario: 鼠标跟随
- **WHEN** 用户在 Live2D canvas 区域移动鼠标
- **THEN** Live2D 模型的眼睛和头部参数跟随鼠标位置偏转，使用 `model.focus(x, y)` 方法

## ADDED Requirements

### Requirement: 默认模型路径修正
Live2DRenderer 的默认模型路径 SHALL 指向实际存在的模型文件。

#### Scenario: 使用正确的默认模型
- **WHEN** 未配置自定义模型路径
- **THEN** 默认加载 `live2d/haru/haru_greeter_t03.model3.json`（该文件实际存在于 public/live2d/haru/ 目录）
