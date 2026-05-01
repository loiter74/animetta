## Solution

使用 Python + Pillow 批量处理图标图片，核心流程：

### 1. 图片去底算法

对于每个 JPEG 图标（RGB，无 Alpha）：
1. 读取原始图片
2. 添加 Alpha 通道
3. 遍历所有像素，将与白色接近的像素（R>240, G>240, B>240）设为全透明
4. 边缘使用抗锯齿过渡（feather），避免硬边
5. 保存为 PNG（带 Alpha）

### 2. 缩放策略

- 目标尺寸：64×64（保留细节，CSS 会进一步缩放到 12-16px）
- 使用 LANCZOS 重采样，保证缩放下图标清晰

### 3. 处理清单

| 类型 | 路径 | 操作 |
|------|------|------|
| 服务图标 | `public/icons/*/*.png` (11个) | 去底 + 缩放 + 转 PNG |
| avatar | `public/avatar/avatar.png` | 检查是否 JPEG，如是则转透明 PNG |
| loading | `public/loading/loading.png` | 同上 |
| error | `public/error/error.png` | 同上 |
| backgrounds | `public/backgrounds/*.png` | 检查是否 JPEG 白底 |
| favicon | `public/favicon.png` | 同上 |

### 4. 验证方式

- 打开 http://localhost:5173/ 确认图标不再显示为白块
- 检查 SettingsPanel 所有服务图标、Tab 图标、记忆按钮显示正常
- 检查不同背景色下图标边缘无硬边/白晕

## Files Changed

| File | Action |
|------|--------|
| `public/icons/asr/asr.png` | regenerate |
| `public/icons/background/background.png` | regenerate |
| `public/icons/chat/chat.png` | regenerate |
| `public/icons/controls/controls.png` | regenerate |
| `public/icons/interrupt/interrupt.png` | regenerate |
| `public/icons/live2d/live2d.png` | regenerate |
| `public/icons/llm/llm.png` | regenerate |
| `public/icons/memory/memory.png` | regenerate |
| `public/icons/persona/persona.png` | regenerate |
| `public/icons/tts/tts.png` | regenerate |
| `public/icons/vad/vad.png` | regenerate |
| `public/avatar/avatar.png` | check + fix if needed |
| `public/loading/loading.png` | check + fix if needed |
| `public/error/error.png` | check + fix if needed |
