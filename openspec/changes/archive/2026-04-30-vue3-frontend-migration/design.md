## Context

Anima 前端当前是纯 Electron + vanilla JS/HTML/CSS，约 40 个源文件。两个独立窗口（Live2D + Chat），使用 pixi.js 渲染 Live2D，Socket.IO 与 Python 后端通信。

后端技术栈（Python/FastAPI/Socket.IO）和 WebSocket 事件协议保持不变。本次只替换前端。

参考项目 AIRI（moeru-ai/airi）使用 Vue 3 + TypeScript + Vite + UnoCSS 架构，日系二次元视觉风格，多平台支持。

## Goals / Non-Goals

**Goals:**
- 将前端从 vanilla JS 迁移到 Vue 3 + TypeScript，体现现代前端工程能力
- 实现日系二次元 + glassmorphism 视觉风格，便于面试官快速感知项目品质
- 单窗口默认布局 + Live2D 可弹出分离，展示灵活的架构设计
- 代码结构清晰，组件边界明确，TypeScript 类型自文档化
- 保留所有现有功能：Live2D 渲染、聊天、语音输入、流式输出、表情系统

**Non-Goals:**
- 不改后端代码和 API 协议
- 不做多平台（Web/Mobile）支持，专注 Electron Desktop
- 不做 SSR 或 Nuxt 集成
- 不替换 Live2D 渲染引擎（继续用 pixi.js + pixi-live2d-display）
- 不做国际化（i18n）

## Decisions

### D1: electron-vite 作为构建工具

**选择**: electron-vite
**替代方案**: 手动 Vite + electron-builder 配置、electron-forge
**理由**: electron-vite 开箱支持 main/renderer/preload 三进程分离、Vue 3 集成、TypeScript、HMR。是当前社区最主流的 Electron + Vue 方案，面试官熟悉。

### D2: 单窗口 + 可弹出 Live2D 架构

**选择**: 默认单窗口布局（左侧 Live2D + 右侧聊天面板），支持点击按钮将 Live2D 弹出为独立窗口
**替代方案**: 固定双窗口、固定单窗口
**理由**: 单窗口展示更直观（面试官一眼看到完整功能），弹出模式保留 Live2D 全屏展示的灵活性。弹出时两个窗口通过 IPC 同步状态。

### D3: 日系二次元 + glassmorphism 主题

**选择**: 深色底 + 半透明毛玻璃面板 + 柔和渐变 + 粉色/紫色/蓝色系强调色
**替代方案**: 科技暗黑风、简约现代风
**理由**: 匹配 VTuber 项目气质，视觉辨识度高，面试官印象深刻。参考 AIRI 和 Cookard 的设计语言。

### D4: 状态管理分层

**选择**: Pinia 管理全局共享状态（socket 连接、聊天历史、Live2D 配置），Composables 管理局部 UI 逻辑（单个组件的状态）
**替代方案**: 纯 Pinia、纯 Composables、Vuex
**理由**: Vue 社区最佳实践。Pinia 的 TypeScript 推断和 DevTools 集成好，composable 轻量适合局部逻辑。

### D5: Socket.IO 封装策略

**选择**: `useSocket` composable 提供连接管理，`useChat` composable 封装聊天事件，`chatStore` (Pinia) 持有消息列表
**替代方案**: 单一 Socket service class、直接在每个组件中调用
**理由**: 分层清晰——连接层、业务层、状态层各司其职，便于测试和维护。

### D6: Live2D 组件封装

**选择**: `<Live2DRenderer>` Vue 组件封装 pixi.js Application 和 pixi-live2d-display，通过 props/emits 暴露控制接口
**替代方案**: 直接在 Vue 中操作 DOM、使用 Web Worker 隔离渲染
**理由**: Vue 组件化封装提供声明式 API，props 驱动表情/模型切换，emits 回传加载状态和交互事件。

### D7: 项目目录结构

```
frontend/
├── electron/                    # Electron 主进程
│   ├── main.ts                  # 应用入口
│   ├── window-manager.ts        # 窗口管理（主窗口 + 弹出窗口）
│   └── preload.ts               # Context bridge
├── src/                         # Vue 3 渲染进程
│   ├── App.vue                  # 根组件
│   ├── main.ts                  # Vue 入口
│   ├── components/              # UI 组件
│   │   ├── chat/                # 聊天相关
│   │   │   ├── ChatPanel.vue
│   │   │   ├── MessageList.vue
│   │   │   ├── MessageBubble.vue
│   │   │   ├── InputBar.vue
│   │   │   ├── VoiceButton.vue
│   │   │   └── TypingIndicator.vue
│   │   ├── live2d/              # Live2D 相关
│   │   │   ├── Live2DRenderer.vue
│   │   │   ├── Live2DControls.vue
│   │   │   └── PopOutButton.vue
│   │   ├── layout/              # 布局
│   │   │   ├── AppLayout.vue
│   │   │   ├── TitleBar.vue
│   │   │   └── StatusBar.vue
│   │   └── shared/              # 通用组件
│   │       ├── GlassPanel.vue
│   │       └── AnimatedButton.vue
│   ├── composables/             # Vue Composables
│   │   ├── useSocket.ts         # Socket.IO 连接管理
│   │   ├── useChat.ts           # 聊天业务逻辑
│   │   ├── useVoice.ts          # 语音录制
│   │   ├── useLive2D.ts         # Live2D 控制
│   │   └── useAudio.ts          # 音频播放
│   ├── stores/                  # Pinia Stores
│   │   ├── chat.ts              # 聊天消息状态
│   │   ├── connection.ts        # 连接状态
│   │   └── live2d.ts            # Live2D 配置
│   ├── styles/                  # 全局样式
│   │   ├── theme.ts             # UnoCSS 主题 token
│   │   └── animations.css       # 全局动画
│   ├── types/                   # TypeScript 类型
│   │   ├── socket-events.ts     # Socket 事件类型
│   │   ├── chat.ts              # 聊天消息类型
│   │   └── live2d.ts            # Live2D 类型
│   └── env.d.ts                 # 环境类型声明
├── index.html                   # Vite 入口 HTML
├── electron.vite.config.ts      # electron-vite 配置
├── uno.config.ts                # UnoCSS 配置
├── tsconfig.json                # TypeScript 配置
├── package.json
└── resources/                   # 图标等静态资源
```

**理由**: 职责清晰，按功能模块组织，面试官能快速定位。electron/ 和 src/ 分离对应 Electron 的进程模型。

## Risks / Trade-offs

- **[Live2D 库兼容性]** → pixi-live2d-display 是旧版库，与 Vite ESM 打包可能有冲突。缓解：使用 `vite-plugin-static-copy` 将库作为静态资源加载，或使用 script 标签全局引入。
- **[Electron 双窗口状态同步]** → 弹出 Live2D 后两个窗口需要同步表情/模型状态。缓解：通过 IPC (ipcRenderer/ipcMain) 桥接，主窗口发送控制指令，弹出窗口接收并执行。
- **[迁移期间功能中断]** → 前端完全重写期间无法使用旧前端。缓解：新建 `frontend-vue/` 目录开发，完成后替换 `frontend/`。
- **[学习成本]** → 如果不熟悉 Vue 3 Composition API / Pinia / UnoCSS 需要学习。缓解：这些技术文档齐全，社区活跃，上手快。
