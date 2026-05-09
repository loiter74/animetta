## Why

为 Anima 项目添加 Bilibili 直播弹幕接入能力，让 AI 虚拟角色能够实时接收、回应直播间弹幕，实现类似 Neuro-sama 的直播互动体验。目前 Anima 仅支持本地文字/语音对话，缺少与直播平台的对接能力。

## What Changes

- **新建** `BilibiliDanmakuService` — 基于 `bilibili-api-python` 的弹幕接收后端服务
- **新建** 前端弹幕流页面 (`/danmaku`) — Twitch 风格从底部向上滚动的聊天栏
- **新建** 前端可拖拽字幕栏 (`AICaptionBar`) — 显示 AI 对弹幕的回复
- **修改** `RouteHandlers` — 添加 `danmaku` 和 `danmaku.ai_reply` Socket.IO 事件
- **修改** `SessionManager` — B站弹幕服务的生命周期管理
- **新增** `config/config.yaml` 的 `bilibili` 配置段
- **新增** `bilibili-api-python` 依赖

## Capabilities

### New Capabilities
- `bilibili-danmaku-service`: 后端 Bilibili 直播弹幕接收、解析、队列管理、生命周期
- `danmaku-stream-page`: 前端独立弹幕流页面，Twitch 风格滚动聊天栏
- `ai-danmaku-response`: AI 逐条响应弹幕 + 可拖拽字幕栏显示回复

### Modified Capabilities
- (无)

## Impact

- **Backend**: `src/anima/orchestration/server/routes.py` — 新事件注册；`session.py` — 生命周期管理；新建 `src/anima/services/live/` 模块
- **Frontend**: 新增路由 `/danmaku`；新建 3 个组件 + 1 个 composable + 1 个 store
- **Config**: `config/config.yaml` 增加 `bilibili` 段
- **Dependencies**: 增加 `bilibili-api-python`
