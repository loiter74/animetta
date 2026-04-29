## 1. 项目脚手架搭建

- [x] 1.1 在项目根目录创建 `frontend-vue/` 目录，使用 `npm create @quick-start/electron` 初始化 electron-vite + Vue 3 + TypeScript 项目
- [x] 1.2 配置 `electron.vite.config.ts`：设置 main/renderer/preload 入口、输出路径、外部依赖排除
- [x] 1.3 配置 `tsconfig.json` 和 `tsconfig.node.json`：启用 strict mode，配置路径别名 `@/` 指向 `src/`
- [x] 1.4 安装并配置 UnoCSS：安装 `unocss` + `@unocss/preset-uno` + `@unocss/preset-icons`，创建 `uno.config.ts`
- [x] 1.5 创建项目目录结构：`components/{chat,live2d,layout,shared}`、`composables/`、`stores/`、`types/`、`styles/`
- [x] 1.6 创建 `env.d.ts` 声明 `.vue` 模块类型和 UnoCSS 类型
- [x] 1.7 验证 `pnpm dev` 能正常启动 Electron + Vite HMR

## 2. 主题与样式系统

- [x] 2.1 在 `uno.config.ts` 中定义日系二次元主题色 token（背景色、文字色、强调色、面板色、边框色）
- [x] 2.2 创建 `styles/theme.ts`：导出主题常量和 CSS 变量定义
- [x] 2.3 创建 `styles/animations.css`：定义消息入场、脉冲、波形、淡入淡出等 keyframes
- [x] 2.4 创建 `<GlassPanel>` 通用组件：半透明背景 + backdrop-filter blur + 微弱边框发光
- [x] 2.5 创建 `<AnimatedButton>` 通用组件：hover/active 过渡动画
- [x] 2.6 配置全局字体（系统字体栈），确保中英文显示正常

## 3. Electron 窗口管理

- [x] 3.1 实现 `electron/window-manager.ts`：管理主窗口创建（无边框、自定义标题栏、初始大小 1200x800）
- [x] 3.2 实现主窗口 `<TitleBar>` 组件：拖拽区域、应用名称、连接状态灯、最小化/关闭按钮
- [x] 3.3 实现 `electron/preload.ts`：暴露 IPC API（弹出窗口控制、窗口操作）
- [x] 3.4 实现弹出窗口功能：点击按钮将 Live2D 渲染移到新 BrowserWindow（AppLayout 弹出/收回逻辑完成）
- [x] 3.5 实现弹出窗口关闭回收：关闭弹出窗口时 Live2D 回到主窗口
- [x] 3.6 实现主窗口与弹出窗口 IPC 状态同步（表情、模型控制指令转发）

## 4. Socket.IO 通信层

- [x] 4.1 创建 `types/socket-events.ts`：定义所有 Socket.IO 事件的 TypeScript 类型
- [x] 4.2 实现 `composables/useSocket.ts`：连接管理、断线重连、连接状态 ref
- [x] 4.3 实现 `stores/connection.ts` (Pinia)：持有连接状态、后端 URL、延迟信息
- [x] 4.4 实现 `composables/useChat.ts`：发送文本、接收流式回复、接收完整回复、中断信号
- [x] 4.5 实现 `composables/useVoice.ts`：麦克风录制、VAD 音量检测、音频数据发送
- [x] 4.6 实现 `composables/useAudio.ts`：TTS 音频播放、播放状态管理
- [x] 4.7 验证：启动后端，前端能连接 Socket.IO 并收发消息

## 5. Live2D Vue 组件

- [x] 5.1 创建 `types/live2d.ts`：Live2D 模型配置、表情类型、口型数据类型定义
- [x] 5.2 实现 `<Live2DRenderer>` 组件：封装 pixi.js Application 创建、Live2D 模型加载、canvas 渲染
- [x] 5.3 处理 pixi-live2d-display 的 Vite 打包兼容性（静态资源加载或 script 标签引入）
- [x] 5.4 实现模型加载状态管理（loading/loaded/error）和 emit 事件
- [x] 5.5 实现表情控制：通过 prop 接收表情指令，驱动 Live2D 表情动画
- [x] 5.6 实现口型同步：根据 TTS 音频数据驱动嘴部参数
- [x] 5.7 实现自动行为：自动眨眼、鼠标注视跟踪、空闲眼球运动（通过 ExpressionController ticker）
- [x] 5.8 实现响应式缩放：监听容器 resize，pixi.js renderer 自适应

## 6. 聊天 UI 组件

- [x] 6.1 创建 `types/chat.ts`：消息类型（user/assistant/system）、消息状态（streaming/complete）
- [x] 6.2 实现 `stores/chat.ts` (Pinia)：消息列表管理、当前流式消息、消息增删改查
- [x] 6.3 实现 `<MessageList>` 组件：渲染消息列表、自动滚动、空状态、翻页不强制滚动
- [x] 6.4 实现 `<MessageBubble>` 组件：用户/AI 气泡区分、流式打字效果、时间戳、完成状态
- [x] 6.5 实现 `<InputBar>` 组件：textarea 自适应增高、Enter 发送、Shift+Enter 换行、发送按钮
- [x] 6.6 实现 `<VoiceButton>` 组件：录音状态切换、音量条动画、麦克风权限处理
- [x] 6.7 实现 `<TypingIndicator>` 组件：三个跳动圆点动画
- [x] 6.8 实现 `<SpeakingIndicator>` 组件：波形动画，TTS 播放时显示

## 7. 应用布局与集成

- [x] 7.1 实现 `<AppLayout>` 组件：左侧 Live2D 区域 + 右侧聊天面板的响应式布局
- [x] 7.2 实现 `<StatusBar>` 组件：显示连接状态指示灯（绿/红/黄）（已集成在 TitleBar 中）
- [x] 7.3 实现 `<Live2DControls>` 组件：Live2D 弹出按钮、缩放控制（PopOutButton 组件）
- [x] 7.4 组装 `<App.vue>` 根组件：集成 AppLayout、TitleBar、全局状态初始化
- [x] 7.5 配置 `main.ts`：创建 Vue app、注册 Pinia、导入 UnoCSS

## 8. 功能特性迁移

- [x] 8.1 迁移风格迁移（Style Transfer）开关功能
- [x] 8.2 迁移记忆整理按钮和进度提示功能
- [x] 8.3 迁移中断信号发送功能
- [x] 8.4 验证所有现有 WebSocket 事件正常工作

## 9. 启动脚本适配与清理

- [x] 9.1 适配 `scripts/start.py`：修改前端启动命令从 `electron .` 改为 `pnpm dev`
- [x] 9.2 将 `frontend-vue/` 重命名为 `frontend/`（备份旧 `frontend/` 为 `frontend-legacy/`）
- [x] 9.3 更新 `.gitignore`、`package.json`（根目录）中相关路径
- [x] 9.4 更新 `CLAUDE.md` 中前端相关文档（架构、命令、目录结构）
- [x] 9.5 端到端测试：`python scripts/start.py` 完整启动流程验证
