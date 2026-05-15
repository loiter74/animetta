## Context

Anima 项目经过 49 次迭代，功能层面已经成熟，但工程质量有四个明显短板需要补课：

- **A. 测试覆盖**：comprehensive-test-coverage 变化已启动（设计 102 项任务），完成了 4 项，余 98 项。核心模块 core/services/memory/tools/avatar/config 大多处于零覆盖到低覆盖状态。
- **B. 前端测试**：前端 57 个文件（Vue 组件 + Pinia stores + composables），0 测试。Live2D 渲染、聊天界面、设置面板均无自动化防护。无 E2E 测试。
- **C. 架构治理**：routes.py 1377 行，包含 Socket.IO 事件处理、B站弹幕、Live2D 回调等混合职责。silero_vad.py（454 行）和 openai_llm.py（430 行）也超出单一职责边界。~15 个测试存在隔离或 mock 问题。
- **D. 开发者体验**：CI 只跑后端测试；前端无 CI 检查；coverage 无门禁；docs/README.md 引用已删除模块。

## Goals / Non-Goals

**Goals:**
- 将 comprehensive-test-coverage 的 98 项剩余任务推进至完成（80%+ 语句覆盖）
- 前端测试从 0 到覆盖全部核心 stores、组件和 composables
- 建立前端 E2E 测试（Playwright）
- routes.py 拆分为可维护的 handler 模块（每个 < 300 行）
- silero_vad.py / openai_llm.py 按职责拆分
- 修复已知的 mock 和测试隔离问题
- 前端 CI（type check + lint + test）集成到 GitHub Actions
- coverage fail_under 逐步提升至 80%
- 更新过时文档

**Non-Goals:**
- 不改动生产代码逻辑（纯新增测试 + 纯提取重构）
- 不引入新的外部依赖（测试工具除外）
- 不涉及性能/压力测试
- 不涉及集成测试（连接真实 API）
- 不修改数据库 schema
- 不涉及功能迭代

## Decisions

### 1. 前端测试框架：vitest + vue-test-utils + happy-dom
- **选择**：vitest 替代 jest。vitest 与 Vite 共享配置、原生 TypeScript 支持、更快的热重载
- **替代方案**：jest + ts-jest → 配置复杂、速度慢。Cypress → 更适合 E2E，不适用于单元测试
- **原因**：vitest 是 Vite 生态标准选择，community 活跃度高，与项目现有 vite.config.ts 无缝集成

### 2. 前端 E2E：Playwright
- **选择**：Playwright 替代 Cypress
- **原因**：Playwright 已在本项目 QA 中使用，本地已安装。支持多浏览器、网络拦截、速度更快
- **替代方案**：Cypress → 社区大但速度慢、配置重。Puppeteer → 功能弱于 Playwright

### 3. routes.py 拆分策略：按 Socket.IO 事件领域拆分
- **方案**：保留 routes.py 作为入口注册点，将 handler 逻辑提取到 `server/handlers/` 目录下
- **拆分维度**：chat_handlers.py（文本/音频输入）、bilibili_handlers.py（B站弹幕）、live2d_handlers.py（Live2D 动作回调）、admin_handlers.py（管理/bilibili 控制）
- **不采用**：单文件全量重写 → 风险高。按行号分批提取 → 过渡期太长

### 4. 大文件拆分：纯提取，不重构逻辑
- **silero_vad.py**: 将 VAD 逻辑提取到 `vad/` 包内：`detector.py`（检测逻辑）+ `processor.py`（音频处理）
- **openai_llm.py**: 将流式生成、工具调用、历史管理提取到 `llm/` 子模块
- **原则**：先提取再优化。第一波只做纯移动，不影响功能

### 5. CI 策略：增量集成
- **前端 CI**：新 workflow `frontend.yml`，与后端独立，不互相阻塞
- **Coverage 门禁**：在现有 `test.yml` 中增加 coverage 步骤，fail_under 从 70% → 逐步升至 80%
- **不采用**：合并为一个巨型 workflow → 调试困难。阻塞式合并门禁 → 开发体验差

### 6. comprehensive-test-coverage 协同策略
- 本变化不重新创建 comprehensive-test-coverage 已有的测试任务
- 本变化增加 coverage CI 门禁和前端测试（comprehensive-test-coverage 不覆盖前端）
- 两个变化独立推进，在 CI 集成点交汇

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| routes.py 拆分可能遗漏导入/注册 | 拆分前先梳理所有 @router 和 socketio.on 注册点，确保覆盖 |
| 前端测试基础设施搭建与现有 Vite 配置冲突 | 先在独立分支验证 vitest 配置，确保与 vite.config.ts 兼容 |
| 大文件拆分导致 git blame 丢失 | 使用 `git blame -C` 可追溯，在 commit message 中注明来源文件 |
| 并行执行多个任务可能产生代码冲突 | Wave 1 任务（B1/C1/C2/D4）无文件重叠，可安全并行 |
| comprehensive-test-coverage 与本变化交接不清 | 明确边界：本变化不包含 comprehensive-test-coverage 中的测试编写任务 |
| 前端测试 mock Live2D 复杂 | 使用 pixi-live2d-display 的 mock 或者对外部库整体 mock |

## Migration Plan

1. **Wave 1**（全部并行，无交叉）：
   - B1: 前端测试基础设施搭建
   - C1: routes.py 拆分
   - C2: 大文件拆分
   - A-A1: 继续 comprehensive-test-coverage 的核心测试
   - D4: 文档更新

2. **Wave 2**（依赖 Wave 1）：
   - B2-B4: 前端 stores/组件/composables 测试
   - A-A2: 修复失败测试（依赖基础设施完备）
   - C3: 测试隔离问题修复
   - D1/D2: CI 前端/coverage 门禁

3. **Wave 3**：
   - B5: E2E 测试
   - 剩余文档收尾

## Open Questions

- Playwright 在 headless Windows 下 Live2D canvas 能否正常渲染？
- frontend-test-infra 是否需要 mock Live2D Cubism Core（.moc3 文件）？
- coverage fail_under 初始值设定在多少合适（考虑当前 ~70%）？
