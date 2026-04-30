## MODIFIED Requirements

### Requirement: 单窗口默认布局
系统 SHALL 默认以单窗口模式启动。窗口布局采用全屏 Live2D 场景 + 右侧浮动交互面板模式，Live2D 模型占满整个视口。

#### Scenario: 应用启动
- **WHEN** Electron 应用启动
- **THEN** 显示单窗口，Live2D 模型占满整个视口区域，右侧浮动 InteractivePanel（可折叠），顶部为毛玻璃 TitleBar

#### Scenario: 窗口大小调整
- **WHEN** 用户拖拽窗口边缘调整大小
- **THEN** Live2D canvas 自适应新尺寸，InteractivePanel 保持固定宽度和相对位置

#### Scenario: 默认窗口尺寸
- **WHEN** 应用首次启动（无保存的窗口位置）
- **THEN** 窗口尺寸为 1280×800，居中显示
