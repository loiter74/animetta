## Why

当前前端使用纯 Electron + vanilla JS/HTML/CSS 构建，缺乏组件化架构和类型系统，导致代码可读性差、维护困难，且视觉效果简陋。面试展示时无法体现现代前端工程能力。需要迁移到 Vue 3 + TypeScript 技术栈，参考 AIRI 项目的日系二次元 UI 风格，打造一个既好看又能展示工程能力的专业前端。

## What Changes

- **BREAKING**: 移除整个 `frontend/` 目录下的 vanilla JS 代码，使用 Vue 3 + TypeScript + electron-vite 重建
- 新建 electron-vite 项目结构（main / renderer / preload 三进程分离）
- 引入 UnoCSS 原子化样式引擎，实现日系二次元 + glassmorphism 视觉风格
- 引入 Pinia 状态管理（全局共享状态）+ Composables（局部 UI 逻辑）
- 实现「单窗口 + 可弹出 Live2D」的窗口架构（默认单窗口布局，支持分离模式）
- 保留 pixi.js + pixi-live2d-display 渲染核心，封装为 Vue 3 组件
- 保留 Socket.IO Client 通信层，封装为 Composable + Pinia Store
- 重写 Chat UI（消息列表、输入栏、语音按钮、打字指示器等）
- 新增连接状态面板、设置面板、情绪可视化等 UI 组件

## Capabilities

### New Capabilities
- `vue3-project-scaffold`: electron-vite 项目脚手架，包含 main/renderer/preload 进程分离、TypeScript 配置、UnoCSS 配置
- `window-manager`: 窗口管理系统，支持单窗口默认布局 + Live2D 弹出分离模式
- `live2d-vue-component`: Live2D 渲染封装为 Vue 3 组件（pixi.js + pixi-live2d-display），支持模型加载、表情切换、口型同步
- `socket-composable`: Socket.IO 通信层封装为 Vue Composable + Pinia Store，对接后端事件协议
- `chat-ui`: 聊天界面组件系统（消息列表、输入栏、语音录制、流式输出、打字指示器）
- `anime-theme`: 日系二次元 + glassmorphism 主题系统（UnoCSS presets、CSS tokens、动画）

### Modified Capabilities
<!-- 无已有 spec 需要修改 -->

## Impact

- **前端代码**: `frontend/` 目录完全重建（~40 个文件 → ~80+ 个 Vue/TS 文件）
- **后端代码**: 无变动，Socket.IO 事件协议不变
- **依赖变化**: 移除 `electron-store`（旧），新增 `vue`、`pinia`、`electron-vite`、`unocss`、`@unocss/preset-uno` 等
- **构建流程**: 从 `electron .` 改为 `electron-vite dev` / `electron-vite build`
- **开发体验**: 新增 HMR 热更新、TypeScript 类型检查、Vue DevTools
- **启动脚本**: `scripts/start.py` 需要适配新的前端启动命令
