## 0. 前置修复：前端端口冲突

- [x] 0.1 修改 `frontend/vite.config.ts`：`port: 3000` → `port: 5173`，同时更新所有相关引用
- [ ] 0.2 验证：`pnpm dev` 启动在 5173，代理 `/api` + `/socket.io` 到后端正常

## 1. 接通 OTel Pipeline（新任务 — 代码核心断点）

- [x] 1.12 在 `socketio_server.py` 的 `get_asgi_app()` 中添加 `init_tracing()` 调用（从 `anima.tracing` import）
- [ ] 1.13 验证 `init_tracing()` 优雅降级：OTel Collector 未启动时，不阻塞启动流程，metrics 静默 NoOp

## 2. LLM Token/Cost 埋点（原 2.5-2.7 — 代码已存在）

- [x] 2.5 修改 `openai_llm.py`：在 `chat()` / `chat_with_tools()` 返回前提取 `response.usage`（prompt_tokens / completion_tokens），调用 `get_llm_tokens().add()` + `get_llm_cost().add()` + `get_llm_errors()` **（代码已存在）**
- [x] 2.6 修改 `openai_llm.py`：在 `chat_stream()` 中从最后一帧提取 usage，记录相同指标 **（代码已存在）**
- [x] 2.7 修改 `glm_llm.py`：将 `_track_usage()` 对接到 metrics pipeline **（代码已存在）**

## 3. RAG / Tool / Session 埋点（原 2.8-2.12 — 代码已存在）

- [x] 3.1 修改 `llm_node.py`：在 RAG 检索计时附近添加 `anima_rag_retrieval_duration_seconds` + `anima_rag_chunks_retrieved` + `anima_rag_top_score` **（代码已存在，修复了 metadata 变量 bug）**
- [x] 3.2 修改 `tool_node.py`：在工具循环中添加 `anima_tool_calls_total` + `anima_tool_duration_seconds` **（代码已存在）**
- [x] 3.3 修改 `routes.py`：在 `on_connect`/`on_disconnect` 添加 `anima_active_sessions`；消息处理添加 `anima_session_messages_total`；错误处理添加 `anima_websocket_errors_total` **（代码已存在）**

## 4. Loki 日志接入

- [x] 4.1 在 `socketio_server.py` 启动入口添加 `logger.add("logs/anima.log", rotation="10MB", retention="7 days")`，输出日志到文件
- [x] 4.2 编写 `observability/loki-config.yaml`（Loki 本地存储配置）
- [x] 4.3 更新 `observability/otel-collector-config.yaml`：添加 filelog receiver，tail `logs/anima.log`，通过 loki exporter 发送
- [x] 4.4 更新 `observability/docker-compose.yml`：新增 Loki 服务 + OTel Collector 挂载 logs 目录
- [x] 4.5 更新 Grafana datasource provision：添加 Loki 数据源

## 5. Notifier 通用通知框架（Python 端）

- [x] 5.1 创建 `src/anima/notifier/` 包（`__init__.py`, `base.py`, `manager.py`, `server.py`）
- [x] 5.2 实现 `NotifierBase` ABC：`send(alerts, status) -> bool` 抽象方法
- [x] 5.3 实现 `@register_notifier(name)` 装饰器和全局注册表（复用 ProviderRegistry 模式）
- [x] 5.4 实现 `Alert` dataclass 和 `parse_alertmanager_payload()` 解析器
- [x] 5.5 实现 `NotifierManager`：加载配置、遍历渠道、并发调用各 notifier
- [x] 5.6 实现 `create_notifier_app()`：独立 Starlette ASGI 应用，监听 `:9094`，暴露 `/api/v1/alerts` webhook 端点
- [x] 5.7 编写 `observability/Dockerfile.notifier`：基于 `python:3.13-slim`，打包 `src/anima/notifier/`
- [x] 5.8 在 `requirements.txt` 添加 httpx 依赖

## 6. 通知插件：Discord + 飞书 + Email

- [x] 6.1 创建 `src/anima/notifier/discord.py`：`@register_notifier("discord")`，Alertmanager → Discord embed 格式转换，颜色编码（critical=red, warning=yellow, resolved=green），httpx POST
- [x] 6.2 创建 `src/anima/notifier/feishu.py`：`@register_notifier("feishu")`，Alertmanager → 飞书 interactive card 转换，HMAC-SHA256 签名校验，post 富文本 fallback，字段截断
- [x] 6.3 创建 `src/anima/notifier/email.py`：`@register_notifier("email")`，SMTP STARTTLS(587)/SSL(465)，multipart/alternative（纯文本 + HTML Jinja2 模板），`asyncio.to_thread()` 包装
- [x] 6.4 创建 `src/anima/notifier/templates/email_alert.html`：Jinja2 HTML 邮件模板

## 7. Notifier Docker 部署 + Alertmanager 路由

- [x] 7.1 更新 `observability/docker-compose.yml`：新增 `notifier` service（Dockerfile.notifier 构建，`:9094`，env_file: `.env.notifier`，网络接入 observability_default）
- [x] 7.2 创建 `.env.notifier`：仅含 `NOTIFIER_*` 和 `ALERT_*` 环境变量，不暴露 LLM API Key
- [x] 7.3 修改 `observability/alertmanager.yml`：webhook receiver 指向 `http://notifier:9094/api/v1/alerts`
- [x] 7.4 在 `.env.example` 新增所有 `NOTIFIER_*` + `ALERT_SMTP_*` 变量

## 8. 验收

- [x] 8.1 完整启动：`docker-compose -f observability/docker-compose.yml up -d` + `pnpm dev`（:5173）+ `python -m anima.socketio_server`
- [x] 8.2 跑一次对话 → Grafana Explore Tempo 能搜到完整 trace
- [x] 8.3 `curl localhost:9090/api/v1/label/__name__/values | grep anima_` 能列出 20+ 指标
- [x] 8.4 Grafana 4 张 dashboard 有数据
- [ ] 8.5 手动断 LLM API key → 触发错误 → 5 分钟内 Discord 收到通知（需配置 .env.notifier）
- [ ] 8.6 飞书群收到通知（需配置飞书 webhook）
- [ ] 8.7 邮箱收到通知（需配置 SMTP）
- [x] 8.8 `python -m pytest tests/ -k "notifier"` 全部通过（21 tests, 21 passed）

## 9. README 更新

- [ ] 9.1 更新 `README.md` observability 章节：端口表（前端:5173, Grafana:3000, Notifier:9094），Loki 接入说明，告警配置（Discord/飞书/Email 三种方式）
- [ ] 9.2 新增 `.env.notifier` 使用说明
