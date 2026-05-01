## MODIFIED Requirements

### Requirement: avatar/loading/error 图片格式
avatar、loading 和 error 图片 SHALL 使用带 Alpha 通道的 PNG 格式。
图片 SHALL 去除白色背景，确保在暗色主题下显示正常。

#### Scenario: 图片在暗色主题下显示
- **WHEN** 图片在暗色主题 UI 中渲染
- **THEN** 背景透明的图片 SHALL 显示清晰，无白色块

### Requirement: 背景图片
背景图片 SHALL 为有效图片格式（JPEG 或 PNG），能被浏览器正常加载渲染。
背景图片 SHALL 无异常全白问题。

#### Scenario: 背景图在设置面板中预览
- **WHEN** BackgroundSettings 组件加载 `/backgrounds/{name}.png`
- **THEN** 图片 SHALL 正常显示缩略图预览

### Requirement: favicon
favicon SHALL 为 PNG 格式，能被浏览器识别。
favicon SHALL 无白色实心背景。

#### Scenario: favicon 在浏览器标签页显示
- **WHEN** 浏览器打开 Anima 页面
- **THEN** 标签页图标 SHALL 可见，非白色方块
