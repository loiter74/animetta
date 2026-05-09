## 1. Backend — BilibiliDanmakuService 核心

- [x] 1.1 创建 `src/anima/services/live/bilibili_danmaku.py` — BilibiliDanmakuService 类（独立线程 + LiveDanmaku 连接）
- [x] 1.2 实现 DANMU_MSG 事件解析与格式化（text, user_name, user_id 提取）
- [x] 1.3 实现 asyncio.Queue 跨线程消息队列管理（FIFO 消费 + 100 条上限）
- [x] 1.4 实现连接失败重试逻辑（指数退避，最多 5 次）
- [x] 1.5 实现优雅关闭（disconnect + queue 清理）
- [x] 1.6 创建 `src/anima/services/live/__init__.py`

## 2. Backend — Socket.IO 事件集成

- [x] 2.1 在 `routes.py` 中添加 DanmakuConsumer（queue consumer，emit `danmaku` + `danmaku.status`）
- [x] 2.2 集成 LangGraph 调用：弹幕 → `orchestrator.process_text()` → emit `danmaku.ai_reply`
- [x] 2.3 在 `session.py` 中添加 BilibiliService 生命周期（init/cleanup）
- [x] 2.4 在 `websocket.py` 中初始化 Bilibili 服务

## 3. Backend — 配置与依赖

- [x] 3.1 在 `config/config.yaml` 添加 `bilibili` 配置段（enabled, room_id, sessdata）
- [x] 3.2 在 `requirements.txt` 添加 `bilibili-api-python`
- [x] 3.3 验证 pip 安装后 import 正常

## 4. Frontend — Danmaku 弹幕流页面

- [x] 4.1 创建 `stores/danmaku.ts` — Pinia store（messages[], connected, messageCount）
- [x] 4.2 创建 `composables/useDanmaku.ts` — Socket.IO 事件监听（danmaku, danmaku.status, danmaku.ai_reply）
- [x] 4.3 创建 `types/chat.ts` 添加 DanmakuItem、DanmakuReply 类型定义
- [x] 4.4 创建 `DanmakuStream.vue` — Twitch 风格底部滚动聊天栏（500 条上限，用户名 + 消息）
- [x] 4.5 创建 `DanmakuPage.vue` — 路由组件（全屏布局 + 连接状态）
- [x] 4.6 在 `router/index.ts` 添加 `/danmaku` 路由
- [x] 4.7 添加页眉/导航切换（从主界面可切换到弹幕页面）

## 5. Frontend — AI 回复字幕栏

- [x] 5.1 创建 `AICaptionBar.vue` — 可拖拽字幕栏（position: fixed，监听 danmaku.ai_reply）
- [x] 5.2 实现拖拽功能（mousedown/mousemove/mouseup，viewport 边界约束）
- [x] 5.3 实现 8 秒自动消失 + 新回复替换旧回复
- [x] 5.4 在 `App.vue` 中全局挂载 AICaptionBar

## 6. 验证与测试

- [x] 6.1 后端语法检查通过 (py_compile all files)
- [x] 6.2 TypeScript 类型检查通过 (vue-tsc --noEmit)
- [x] 6.3 bilibili-api-python 导入验证通过
- [x] 6.4 Python 文件编译无错误
- [ ] 6.5 运行时验收：启动后验证弹幕连接与显示（需要 Bilibili 直播间配置）
