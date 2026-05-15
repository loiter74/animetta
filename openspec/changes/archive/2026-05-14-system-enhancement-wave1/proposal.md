## Why

Anima 项目经过 49 次迭代已具备扎实的功能基础，但工程质量存在明显短板：前端零测试覆盖（57 个前端文件无任何防护）、核心路由文件 routes.py 膨胀至 1377 行、~15 个存量测试失败、CI 仅跑后端测试、过时文档未更新。当前综合测试覆盖计划（comprehensive-test-coverage）已启动但还有 98 项任务待完成。现在是时候全面补齐质量、架构和开发者体验的欠账，让系统进入可持续迭代的轨道。

## What Changes

- **A. 测试覆盖收尾**：继续执行 comprehensive-test-coverage 剩余的 core/services/memory/tools/avatar/config 测试编写任务
- **B. 前端测试从零到一**：搭建 vitest + vue-test-utils + happy-dom 测试基础设施，为 Pinia stores、Vue 组件、composables 编写单元测试，引入 Playwright E2E 测试
- **C. 核心架构治理**：将 1377 行 routes.py 按职责拆分为多个 handler 文件；将 silero_vad.py (454 行) 和 openai_llm.py (430 行) 按单一职责拆分；修复已知测试隔离问题
- **D. 开发者体验与 CI 加固**：增加前端 CI（vue-tsc type check + lint + test）、coverage fail_under 逐步提升至 80%、更新过时文档

## Capabilities

### New Capabilities
- `frontend-test-infra`: 前端测试基础设施，含 vitest/vue-test-utils/happy-dom/playwright 配置、CI 集成
- `frontend-store-tests`: Pinia stores (chat/settings/live2d) 的单元测试，含 mock 和状态变更断言
- `frontend-component-tests`: Vue 组件 (chat/live2d/layout/shared) 的渲染和交互测试
- `frontend-composable-tests`: composables (useLive2D 等) 的逻辑单元测试
- `frontend-e2e`: Playwright 端到端测试，覆盖聊天对话、Live2D 渲染、设置页面核心流程
- `routes-refactor`: 将 orchestrator/server/routes.py 按职责拆分为多个 handler 模块
- `large-file-refactor`: 将 silero_vad.py 和 openai_llm.py 按单一职责拆分
- `ci-frontend`: 前端 CI pipeline（type check + lint + test）集成到 GitHub Actions
- `ci-coverage-gate`: coverage fail_under 逐步提升（70% → 80%）并加入 CI
- `docs-update`: 更新 docs/README.md、AGENTS.md 等过时文档，删除已废弃模块引用

## Impact

- 后端模块新增 40-60 个测试文件（通过 comprehensive-test-coverage 推进）
- 前端新增 20-30 个测试文件 + 2-3 个 E2E 测试
- routes.py 拆分为 5-8 个 handler 文件（文件名变化，导入路径需更新）
- 新增 CI workflow 步骤（前端检查 + coverage 门禁）
- 更新 GitHub Actions test.yml
- AGENTS.md 和 README.md 需同步更新
- 不涉及 API 变更、不破坏现有功能
