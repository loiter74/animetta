## Why

Anima 的图标素材在暗色主题下显示为白色块，完全不可见。

**根因分析**：从素材库导入的图标文件存在以下问题：
1. **格式错误** — 源文件虽是 `.png` 后缀，但实际为 JPEG 格式（无 Alpha 透明通道）
2. **白色背景** — 所有图标中心像素为 ~(240,240,240)，即白色/浅灰实心背景
3. **尺寸过大** — 源文件 1024×1024，UI 中仅显示为 12-16px，缩放后只剩白块
4. **暗色主题不兼容** — 白色实心背景在全黑 UI 下完全无法辨识

受影响组件：SettingsPanel（服务图标、Tab 图标）、ChatPanel（记忆按钮）、Live2DRenderer（空闲状态）、InteractivePanel（聊天 Tab）

## What Changes

- **图标去底** — 将所有图标 JPEG 转为真正 PNG，移除白色背景（chroma key），加入 Alpha 透明通道
- **图标缩放到合理尺寸** — 从 1024×1024 缩小至 64×64（留大一点，后续可复用）
- **修复所有引用路径** — 确保所有 `<img>` 标签路径正确
- **同步处理其他素材** — avatar、loading、error 和 background 一并检查处理

## Capabilities

### New Capabilities

- 无

### Modified Capabilities

- `public/icons/*/*.png`：11 个服务图标从白底 JPEG 变为透明 PNG
- `public/avatar/avatar.png`、`public/loading/loading.png`、`public/error/error.png`：同步检查处理
- `public/backgrounds/*.png`：7 张背景图检查是否有同样问题

## Impact

- **修改文件**: `frontend/public/icons/*/` 下 11 个图标文件重新生成
- **无代码改动**：文件路径不变，组件 `<img>` 引用无需修改
- **无新增依赖**：使用 Python PIL/Pillow （已有依赖）处理图片
