## Why

当前测试覆盖率为 **34%**（14,365 语句中 9,485 条未覆盖），远低于生产项目标准。核心模块如 `core/`、`services/`（LLM/ASR/TTS 实现）、`orchestration/server/` 覆盖率均低于 20%，`services/live2d/`、`services/live/`、`tools/custom_tools.py`、`utils/` 甚至为 0%。低覆盖率导致重构风险高、回归难以发现、新人上手困难。目标是达到 **100% 语句覆盖**，确保每个模块都有充分测试。

## What Changes

- 为所有零覆盖率的模块（`core/service_pool.py`、`core/socketio_server.py`、`services/live2d/*`、`services/live/bilibili_danmaku.py`、`tools/custom_tools.py`、`tools/langchain_tools.py`、`tools/config.py`、`utils/*`、`config/user_settings.py`、`memory/prompts.py`、`memory/fuzzy/*`、`services/intelligence/llm/glm_message_converter.py`、`services/intelligence/llm/langchain_adapter.py`）创建初始测试套件
- 为低覆盖率模块补充测试用例，目标 100% 语句覆盖
- 修复现有的 18 个失败测试用例
- 新增 mock 依赖（`pydub` 等）确保测试环境可重复
- 为 `avatar/` 各分析器/映射器/策略类增加核心逻辑测试
- 为 `orchestration/server/` 的路由处理增加 WebSocket 事件模拟测试
- 为 `config/app.py` 的配置加载/环境变量展开逻辑增加测试
- 为 `memory/` 的 learner/engine、wiki/organizer 等底层组件增加测试

## Capabilities

### New Capabilities
- `core-server-test`: ServicePool 和 socketio_server 的启动/关闭生命周期测试
- `service-provider-test`: 所有 LLM/ASR/TTS/VAD 提供商的接口契约测试和各实现的烟雾测试
- `live2d-service-test`: Live2D 动作队列、口型同步、预设加载的单元测试
- `bilibili-danmaku-test`: B站弹幕连接的模拟测试
- `tool-registry-test`: 工具系统（内置工具、MCP 桥、自定义工具、Minecraft 工具）的注册/执行测试
- `utils-test`: auto_config、env_helper、logger_manager 等工具函数测试
- `config-loading-test`: AppConfig 的 YAML 加载、环境变量展开、服务配置解析测试
- `websocket-routes-test`: Socket.IO 事件路由的模拟测试
- `avatar-expression-test`: 表情分析器（LLM-tag、keyword）、映射器、时间线策略的算法测试
- `memory-comprehensive-test`: 记忆系统底层组件（wiki organizer、learner engine、fuzzy models、prompts）的测试
- `existing-test-repair`: 修复 18 个现有失败测试

### Modified Capabilities
<!-- No existing specs need requirement changes - these are purely additive test coverage improvements -->

## Impact

- 测试文件将从 33 个增加到约 60-70 个，测试代码行数从 5,311 行增加到约 15,000 行
- 需要新增 mock 依赖：`pydub`（修复 audio analyzer 测试）
- 覆盖率从 34% 提升至 100%
- 所有现有 18 个失败测试将被修复
- 不会修改任何生产代码（测试是纯新增的）
- 对 CI （GitHub Actions）无影响 — pytest-cov 已配置
