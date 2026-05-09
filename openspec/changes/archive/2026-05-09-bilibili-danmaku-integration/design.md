## Context

Anima 目前支持本地文字和语音对话，通过 LangGraph 编排 LLM 回复，通过 Socket.IO 与前端通信。本项目增加 Bilibili 直播弹幕实时接收与 AI 互动能力。

Bilibili 弹幕系统需要：
- WebSocket 长连接到 Bilibili 弹幕服务器
- Cookie 认证（可选，匿名可读但有限流风险）
- 独立的事件循环（bilibili-api-python 的 LiveDanmaku 是 asyncio 原生）

## Goals / Non-Goals

**Goals:**
- 接收 Bilibili 直播间弹幕并在前端独立页面展示（Twitch 风格底部滚动）
- AI 逐条响应弹幕，回复显示在可拖拽字幕栏
- 与现有对话系统隔离，互不干扰

**Non-Goals:**
- 不发送弹幕回 Bilibili（暂不支持）
- 不实现礼物答谢（后续可扩展）
- 不做弹幕聚合/合并（目前逐条处理）
- 不需要 Electron IPC 变更

## Decisions

### Decision 1: bilibili-api-python vs blivedm
**选择**: `bilibili-api-python`

| 维度 | bilibili-api-python | blivedm |
|------|-------------------|---------|
| 安装 | `pip install bilibili-api-python` | git clone + 手动安装 |
| 事件覆盖 | 50+ (DANMU_MSG, SEND_GIFT, SUPER_CHAT 等) | 基础弹幕 + 心跳 |
| 社区活跃 | 活跃 (6k+ stars, 持续维护) | 维护较少 |
| API 设计 | 装饰器 `@room.on('DANMU_MSG')` | 继承 `BaseHandler` 覆写方法 |

### Decision 2: 独立 worker 线程 + Queue
**选择**: 线程池模式，用 `asyncio.Queue` 跨线程通信

```
Bilibili 线程 (独立 event loop)
  LiveDanmaku → on('DANMU_MSG') → queue.put(msg)
                                         │
                                   asyncio.Queue (跨线程)
                                         │
 主线程 (主 event loop)                   │
  RouteHandlers ← queue consumer ←───────┘
       │
       ├─ socket.emit('danmaku', ...)      → 前端弹幕流页面
       └─ orchestrator.process_text(...)   → AI 回复
                                              → socket.emit('danmaku.ai_reply', ...)
```

理由：`LiveDanmaku.connect()` 是阻塞的 asyncio 调用，不能直接在主事件循环中运行（会阻塞其他 Socket.IO 处理）。线程池模式在 VirtualWife 等项目中被验证有效。

### Decision 3: 独立的弹幕路由 / 事件命名
**选择**: 使用独立路由 `/danmaku` 和独立事件命名空间 `danmaku.*`

理由：
- 弹幕流与主聊天 UI 逻辑分离，互不干扰
- 主聊天已有复杂的 streaming buffer 机制，弹幕不需要
- 用 `danmaku`、`danmaku.ai_reply`、`danmaku.status` 命名清晰

### Decision 4: 弹幕作为 text_input 注入 LangGraph
**选择**: 复用 `orchestrator.process_text()` 接口

弹幕文本直接当作 `text_input` 发给 LLM，走完整的 LangGraph pipeline（LLM → TTS → emotion → output）。不需要改 graph 节点，只需要改调用端。

关键区别：弹幕触发的回复只发 `danmaku.ai_reply` 事件，不走主聊天的 `sentence`/`control` 事件流。

### Decision 5: 前端用独立页面 + 可拖拽字幕
**选择**: 新增路由 `/danmaku` + `AICaptionBar.vue` 组件

- 弹幕流页面：全屏、Twitch 风格、纯显示弹幕
- 字幕栏：用 `v-draggable` 自定义指令实现拖拽，position: fixed 定位
- 不修改 InteractivePanel 现有 tab 结构

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  后端 (Python)                                                │
│                                                              │
│  BilibiliDanmakuService (独立线程)                             │
│  ┌──────────────────────────────────────────────────┐        │
│  │  LiveDanmaku(room_id)                            │        │
│  │  @room.on('DANMU_MSG') → parse → queue.put()    │        │
│  │  @room.on('SEND_GIFT')  → parse → queue.put()   │        │
│  └─────────────┬────────────────────────────────────┘        │
│                │ asyncio.Queue                                │
│  ┌─────────────▼────────────────────────────────────┐        │
│  │  DanmakuConsumer (RouteHandlers 内)              │        │
│  │                                                  │        │
│  │  while running:                                  │        │
│  │    msg = await queue.get()                       │        │
│  │    self.sio.emit('danmaku', msg)  → 前端         │        │
│  │    await orchestrator.process_text(msg.text)     │        │
│  │    self.sio.emit('danmaku.ai_reply', reply) → 前端│        │
│  └──────────────────────────────────────────────────┘        │
│                                                              │
│  生命周期: SessionManager.init_bilibili() / cleanup()         │
│  配置: config/config.yaml → bilibili: {enabled, room_id}     │
└──────────────────────────────────────────────────────────────┘
         │                        │
         │ danmaku event          │ danmaku.ai_reply event
         ▼                        ▼
┌────────────────────┐  ┌──────────────────────────┐
│ 前端 /danmaku 页面  │  │ AICaptionBar.vue         │
│                    │  │                          │
│ DanmakuPanel.vue   │  │ AI 字幕显示              │
│ - Twitch 风格滚动   │  │ - 可拖拽 (position:fixed)│
│ - 500 条上限       │  │ - 8秒自动消失            │
│ - 连接状态指示      │  │ - 新回复替换旧回复        │
└────────────────────┘  └──────────────────────────┘
```

## Data Flow (完整链路)

```
观众发弹幕 "你好啊"
  ↓
Bilibili 弹幕服务器 → LiveDanmaku WebSocket
  ↓
on('DANMU_MSG') → 提取 {text="你好啊", user_name="观众A", user_id=12345}
  ↓
asyncio.Queue.put(msg)
  ↓  (主线程消费)
DanmakuConsumer:
  1. socket.emit('danmaku', {text, user_name, timestamp})  → 前端显示弹幕
  2. orchestrator.process_text(text="观众A说: 你好啊")
     ↓
     LangGraph → LLM → "你好呀！欢迎来到直播间~"
     ↓
  3. socket.emit('danmaku.ai_reply', {
       danmaku_text: "你好啊",
       reply_text: "你好呀！欢迎来到直播间~",
       user_name: "观众A"
     })  → 前端字幕栏显示
```

## File Map

| Layer | File | Description |
|-------|------|-------------|
| Backend | `src/anima/services/live/bilibili_danmaku.py` | BilibiliDanmakuService 主类 |
| Backend | `src/anima/services/live/__init__.py` | 模块导出 |
| Backend | `src/anima/orchestration/server/routes.py` | 添加 `danmaku` consumer 和事件 |
| Backend | `src/anima/orchestration/server/session.py` | B站服务生命周期 |
| Backend | `src/anima/orchestration/server/websocket.py` | 服务初始化 |
| Backend | `config/config.yaml` | 添加 `bilibili` 配置段 |
| Backend | `requirements.txt` | 添加 `bilibili-api-python` |
| Frontend | `frontend/src/views/DanmakuPage.vue` | 弹幕流页面路由组件 |
| Frontend | `frontend/src/components/chat/DanmakuStream.vue` | Twitch 风格弹幕流列表 |
| Frontend | `frontend/src/components/chat/AICaptionBar.vue` | 可拖拽 AI 字幕栏 |
| Frontend | `frontend/src/composables/useDanmaku.ts` | Danmaku Socket.IO composable |
| Frontend | `frontend/src/stores/danmaku.ts` | Danmaku Pinia store |
| Frontend | `frontend/src/router/index.ts` | 添加 `/danmaku` 路由 |
| Frontend | `frontend/src/App.vue` | 添加字幕栏全局组件 |
| Frontend | `frontend/src/types/chat.ts` | 添加 Danmaku 类型 |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| [限流] Bilibili 未登录状态下可能丢弹幕 | 文档说明 SESSDATA 配置方法；匿名可先用 |
| [线程安全] Queue 跨线程数据竞争 | 使用 `asyncio.Queue` + `loop.call_soon_threadsafe` 确保线程安全 |
| [性能] 弹幕高峰期 AI 处理延迟 | 当前逐条处理 + 100 条队列上限，弹幕过多时丢弃旧消息 |
| [依赖] bilibili-api-python 协议变更 | 该库封装了协议细节，API 层变更会自动适配 |

## Open Questions

- 弹幕作为触发时，system prompt 是否需要增加直播场景提示词？（如：你在直播，正在与观众互动）
- AI 回复弹幕时说中文还是跟随模型语言？
