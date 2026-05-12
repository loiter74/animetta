## Context

当前 Anima 项目测试覆盖率为 34%，存在以下问题：
- 18 个测试失败（`test_audio_analyzer.py` 缺少 pydub、`test_memory_entry_store.py` 表结构问题）
- 多个核心模块零覆盖率：`core/socketio_server.py`、`services/live2d/`、`tools/custom_tools.py`、`utils/` 等
- 服务层提供商的接口实现（LLM/ASR/TTS 共 20+ 具体类）缺乏契约测试
- WebSocket 路由层（1092 行 routes.py）只有 9% 覆盖率
- 测试基础设施完善（conftest.py 已有 6 个 mock fixture），但未充分利用

测试策略需要平衡：100% 语句覆盖 ≠ 100% 分支覆盖。目标是对每行代码都有测试覆盖，但外部依赖（API 调用、硬件设备）使用 mock。

## Goals / Non-Goals

**Goals:**
- 整体语句覆盖率从 34% 提升至 100%
- 每个模块至少达到 100% 语句覆盖
- 修复现有 18 个失败测试
- 建立服务提供商的接口契约测试（每个 LLM/ASR/TTS 接口实现都经过基础烟雾测试）
- 为 WebSocket 事件处理建立模拟测试框架
- 所有新增测试只使用 mock，不依赖外部服务
- CI 中 coverage fail_under 逐步提升至 100%

**Non-Goals:**
- 集成测试（连接真实 API/数据库的测试属于单独范畴）
- 前端测试（前端零测试，但本次专注于后端）
- 端到端测试
- 性能/压力测试
- 修改生产代码（纯新增测试）
- 100% 分支覆盖（仅追求 100% 语句覆盖）

## Decisions

### 1. 测试策略：先 mock 后契约
- 对服务提供商（LLM/ASR/TTS/VAD）：只写接口契约测试（确保 `from_config()` 和核心方法正确调用，不验证外部 API 行为）
- 对工具系统：mock 外部 API（web_search mock Tavily/DuckDuckGo），验证 AST 计算器和文件操作的正确性
- 对 WebSocket 路由：使用 `AsyncMock` 模拟 Socket.IO 的 event emission，验证路由逻辑而非 socket 行为
- 对 Live2D 服务：纯逻辑测试（动作队列的入队/出队策略、口型同步算法、预设加载解析）
- 对记忆系统底层：测试 wiki organizer、learner engine 的纯函数逻辑，mock LLM 调用

### 2. 测试文件组织
- 按模块目录组织：`tests/<module>/test_<component>.py`
- 大型文件（如 `routes.py`、`service_context.py`、`orbuilder.py`）拆分为多个测试文件
- 服务提供商测试按类型分组：`tests/services/test_llm_providers.py`、`tests/services/test_tts_providers.py` 等

### 3. 修复策略
- `test_audio_analyzer.py`: 安装 `pydub` 依赖
- `test_memory_entry_store.py`: 在测试 fixture 中初始化 `memory_relations` 表
- 其余失败测试逐一分析修复

### 4. 覆盖率断点（逐步收紧）
CI 逐步收紧 coverage fail_under：
- Phase 1: 34% → 50%
- Phase 2: 50% → 75%
- Phase 3: 75% → 100%

### 5. Mock 架构
扩展现有的 `tests/conftest.py`，新增：
- `mock_embedding()` — 模拟 sentence-transformers 嵌入
- `mock_chroma()` — 模拟 ChromaDB 客户端
- `mock_mcp_client()` — 模拟 MCP 协议连接
- `mock_minecraft_bridge()` — 模拟 Mineflayer 进程
- `mock_bilibili_client()` — 模拟 Bilibili API

## Risks / Trade-offs

- **[风险] 服务层测试覆盖真实 API 调用行为有限** → 采用契约测试 + 烟雾测试方案，确保接口不变；集成测试单独范畴
- **[风险] WebSocket 路由测试涉及大量异步代码** → 使用 `pytest-asyncio` + `AsyncMock`，避免真实连接
- **[风险] 记忆系统测试依赖 ChromaDB/SQLite 文件系统** → 使用 `tmp_path` fixture + 内存 SQLite
- **[风险] mock 过度导致测试失去价值** → 对纯逻辑函数（计算、解析、映射）保持真实调用，只对外部依赖做 mock
- **[风险] 测试数量暴增导致 CI 时间变长** → 利用 pytest-xdist 并行执行；当前 311 个测试 29s，预计增加到 700+ 后约 60s
