## Context

当前 Anima 前端（Vue 3 + Vite）已完成 Socket.IO 直连改造，去掉了 Electron 依赖。但存在以下体验缺失：
- 浏览器标签页无图标
- 背景为纯色 `#1a1028`，不可自定义
- 设置面板所有服务配置显示为 `-`，因无法从后端获取实时配置
- 记忆整理仅有简单进度条，无状态详情展示
- Live2D 拖拽/缩放后没有便捷的一键重置途径

## Goals / Non-Goals

**Goals:**
- 添加浏览器 favicon（SVG 格式，适配 light/dark mode）
- 支持自定义背景图：URL 输入、本地文件上传、3-5 张预设背景
- 设置面板从后端获取并显示真实配置（服务名、角色名、模型路径等）
- 后端暴露 `get_config` → `config_data` socket 事件，返回安全（脱敏）配置
- 记忆整理状态详情展示（当前阶段、进度百分比）
- 一键重置 Live2D 缩放和位置

**Non-Goals:**
- 消息持久化（单独 spec）
- 主题切换/亮暗模式
- 会话历史管理
- 服务配置在线切换（只显示，不修改）

## Decisions

### 1. Favicon：SVG + media 适配
- 使用内嵌 SVG（`favicon.svg`），支持 `prefers-color-scheme` 自动切换亮暗版本
- 放在 `frontend/public/`，Vite 自动 serve
- `index.html` 中 `<link rel="icon" type="image/svg+xml" href="/favicon.svg">`

### 2. 背景图：localStorage 存储 + CSS 变量
- 预设背景图片放 `frontend/public/backgrounds/`（3-5 张暗色调风格匹配的抽象图）
- 用户设置的 URL/file 存储到 `localStorage['anima_background']`
- `App.vue` 根 div 通过 CSS `style` 绑定 `background-image`
- 新建 `BackgroundSettings.vue` 组件，含预设选择、URL 输入、文件上传按钮
- 文件上传使用 `FileReader` 转为 base64 data URL（限制 5MB，存 localStorage 会比较大，但简单可行）

### 3. 后端 get_config：新增 socket 事件
- 在 `routes.py` 的 `WebSocketHandler` 类中新增 `on_get_config` 方法
- 从 `self.global_config` 或 `AppConfig.load()` 读取
- 返回数据结构：
  ```json
  {
    "persona": "neuro-vtuber",
    "services": { "asr": "faster_whisper", "tts": "edge", "agent": "glm", "vad": "silero" },
    "active_services": { "asr": "faster_whisper", "tts": "edge", "llm": "glm", "vad": "silero" },
    "live2d": { "model_path": "/live2d/haru/...", "enabled": true },
    "system": { "host": "0.0.0.0", "port": 12394 },
    "available_personas": ["default", "neuro-vtuber"]
  }
  ```
- **不暴露 API Key、token、本地路径等敏感信息**
- 在 `register_routes` 中注册 `sio.on('get_config')`
- 前端监听 `config_data` 事件

### 4. 记忆整理状态展示
- 利用 socket 事件 `memory.organize.progress` 的 `{text, progress}` 数据
- 在聊天面板中将当前进度条改造为带阶段文本的状态卡片
- 使用已有 `store.memoryOrganizing` 控制显示

### 5. Live2D 视图重置
- 在 Live2D 控件区域（或设置面板）添加"重置视图"按钮
- 调用 `useLive2D` 暴露的 `resetView()` 方法

## Risks / Trade-offs

- **背景图 base64 存储**: 上传图片转 base64 存入 localStorage，如果图片较大（>2MB）可能导致存储空间问题。→ 限制上传 5MB，未来可改为后端存储
- **背景图跨域问题**: URL 输入的外部图片可能因 CORS 无法显示。→ 提示用户使用可公开访问的图片 URL
- **get_config 事件安全性**: 需确保不泄露 API Key 等凭证。→ 返回数据前主动过滤敏感字段
- **后端 global_config 可能为空**: 在 socketio_server 未初始化完成时请求。→ 方法内 fallback 到 `AppConfig.load()`
