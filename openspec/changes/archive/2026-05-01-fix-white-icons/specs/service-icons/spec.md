## MODIFIED Requirements

### Requirement: 服务图标文件格式
所有服务图标 SHALL 使用带 Alpha 通道的 PNG 格式，不得为 JPEG 格式。
图标 SHALL 具有透明背景（白色像素 R>240,G>240,B>240 SHALL 被设为全透明）。
图标尺寸 SHALL 不超过 64×64 像素（使用 LANCZOS 重采样）。
图标去除白底后边缘 SHALL 过渡自然，无白晕残留。

#### Scenario: 图标在暗色主题下显示
- **GIVEN** 图标文件为透明 PNG
- **WHEN** 在 Anima 暗色主题 UI 中以 12-16px 大小显示
- **THEN** 图标 SHALL 可见，非白色方块

#### Scenario: 图标为 JPEG 格式时转换
- **GIVEN** 源文件实际为 JPEG 格式（RGB，无 Alpha）
- **WHEN** 处理图标
- **THEN** SHALL 转换为 PNG 并添加 Alpha 通道，白色背景被移除

### Requirement: 图标文件路径
每个服务类别 SHALL 有对应图标文件于 `frontend/public/icons/{category}/{name}.png`。
路径 SHALL 与组件 `<img :src>` 引用一致。

#### Scenario: 所有服务都有图标
- **WHEN** 列出 `frontend/public/icons/` 下子目录
- **THEN** asr, tts, llm, vad, chat, memory, live2d, persona, background, controls, interrupt SHALL 各有至少一个 `.png` 文件
