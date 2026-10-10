# Animetta 文件索引

扫描日期：2026-10-10（Asia/Shanghai）。用于后续架构定位与阅读导航；目录职责参考现有 module-map.md 和根目录 AGENTS.md，文件列表来自当前工作区。职责说明不代表已逐文件验证依赖关系。

扫描基线提交：`f53f6a891e62f156700660b37ee46d5c5fbd888f`。共 **2063** 个文件；索引自身计入。

范围：Git 跟踪文件及未被忽略的未跟踪文件，仅保留当前存在的文件。排除运行数据、模型、日志、依赖、缓存、构建输出及本地 CodeGraph 数据；不读取配置值或运行数据内容。被 Git 忽略的其他本地文件不在清单内。

未跟踪文件标记为「未提交」，只表示扫描时的状态。已跟踪文件可能包含工作区修改；本索引不是提交内容快照。文件路径相对于仓库根目录，链接指向实际文件。

## 架构阅读入口

| 范围 | 定位 |
| --- | --- |
| 整体边界 | [docs/architecture/module-map.md](../../docs/architecture/module-map.md)：模块所有权与依赖方向 |
| 架构总览 | [docs/architecture/overview.md](../../docs/architecture/overview.md)：现有架构图与说明 |
| 架构决策 | [docs/adrs/README.md](../../docs/adrs/README.md)：ADR 目录 |
| 运行生命周期 | [scripts/runtime_lifecycle.py](../../scripts/runtime_lifecycle.py)：规范生命周期命令 |
| 后端组装 | [src/animetta/orchestration/server/__init__.py](../../src/animetta/orchestration/server/__init__.py)：服务端组合边界 |
| Socket 路由 | [src/animetta/orchestration/server/routes.py](../../src/animetta/orchestration/server/routes.py)：路由注册 |
| 状态图 | [src/animetta/orchestration/graph/builder.py](../../src/animetta/orchestration/graph/builder.py)：LangGraph 构建 |
| 状态定义 | [src/animetta/orchestration/graph/state.py](../../src/animetta/orchestration/graph/state.py)：编排状态 |
| Dashboard 前端 | [frontend/src/main.ts](../../frontend/src/main.ts)：Vue 入口 |
| 直播前端 | [frontend/src/live/main.ts](../../frontend/src/live/main.ts)：直播页面入口 |
| 后端依赖 | [pyproject.toml](../../pyproject.toml)：Python 项目配置 |
| 前端依赖 | [frontend/package.json](../../frontend/package.json)：前端脚本与依赖 |

后续分析先按目录定位，再使用现有 CodeGraph 查询具体符号、调用链与依赖；遇到索引陈旧提示时读取对应当前文件。文件数量只说明目录规模，不代表复杂度或耦合度。

## 顶层目录规模

| 目录 | 文件数 |
| --- | ---: |
| .agents | 91 |
| .github | 5 |
| .vscode | 1 |
| 根目录 | 27 |
| config | 21 |
| contracts | 7 |
| design-system | 34 |
| docker | 6 |
| docs | 130 |
| evaluations | 30 |
| frontend | 398 |
| observability | 14 |
| openspec | 7 |
| pitch | 8 |
| scripts | 52 |
| services | 85 |
| songs | 27 |
| sources | 2 |
| src | 572 |
| tests | 504 |
| tooling | 42 |

## 完整文件清单

### .agents

#### .agents/skills/connect-bilibili-live

- [.agents/skills/connect-bilibili-live/SKILL.md](../../.agents/skills/connect-bilibili-live/SKILL.md)

#### .agents/skills/connect-bilibili-live/agents

- [.agents/skills/connect-bilibili-live/agents/openai.yaml](../../.agents/skills/connect-bilibili-live/agents/openai.yaml)

#### .agents/skills/connect-bilibili-live/scripts

- [.agents/skills/connect-bilibili-live/scripts/bilibili_live.py](../../.agents/skills/connect-bilibili-live/scripts/bilibili_live.py)

#### .agents/skills/efficiency-retrospective

- [.agents/skills/efficiency-retrospective/SKILL.md](../../.agents/skills/efficiency-retrospective/SKILL.md)

#### .agents/skills/efficiency-retrospective/agents

- [.agents/skills/efficiency-retrospective/agents/openai.yaml](../../.agents/skills/efficiency-retrospective/agents/openai.yaml)

#### .agents/skills/json-canvas

- [.agents/skills/json-canvas/SKILL.md](../../.agents/skills/json-canvas/SKILL.md)

#### .agents/skills/operate-anima-runtime

- [.agents/skills/operate-anima-runtime/SKILL.md](../../.agents/skills/operate-anima-runtime/SKILL.md)

#### .agents/skills/operate-anima-runtime/agents

- [.agents/skills/operate-anima-runtime/agents/openai.yaml](../../.agents/skills/operate-anima-runtime/agents/openai.yaml)

#### .agents/skills/operate-anima-runtime/references

- [.agents/skills/operate-anima-runtime/references/commands.md](../../.agents/skills/operate-anima-runtime/references/commands.md)
- [.agents/skills/operate-anima-runtime/references/recovery.md](../../.agents/skills/operate-anima-runtime/references/recovery.md)

#### .agents/skills/qa-testing-playwright

- [.agents/skills/qa-testing-playwright/SKILL.md](../../.agents/skills/qa-testing-playwright/SKILL.md)

#### .agents/skills/qa-testing-playwright/assets

- [.agents/skills/qa-testing-playwright/assets/template-playwright-e2e-review-checklist.md](../../.agents/skills/qa-testing-playwright/assets/template-playwright-e2e-review-checklist.md)
- [.agents/skills/qa-testing-playwright/assets/template-playwright-fail-on-flaky-reporter.js](../../.agents/skills/qa-testing-playwright/assets/template-playwright-fail-on-flaky-reporter.js)
- [.agents/skills/qa-testing-playwright/assets/template-playwright-preflight-checklist.md](../../.agents/skills/qa-testing-playwright/assets/template-playwright-preflight-checklist.md)

#### .agents/skills/qa-testing-playwright/references

- [.agents/skills/qa-testing-playwright/references/api-testing-playwright.md](../../.agents/skills/qa-testing-playwright/references/api-testing-playwright.md)
- [.agents/skills/qa-testing-playwright/references/playwright-authentication.md](../../.agents/skills/qa-testing-playwright/references/playwright-authentication.md)
- [.agents/skills/qa-testing-playwright/references/playwright-ci.md](../../.agents/skills/qa-testing-playwright/references/playwright-ci.md)
- [.agents/skills/qa-testing-playwright/references/playwright-mcp.md](../../.agents/skills/qa-testing-playwright/references/playwright-mcp.md)
- [.agents/skills/qa-testing-playwright/references/playwright-patterns.md](../../.agents/skills/qa-testing-playwright/references/playwright-patterns.md)
- [.agents/skills/qa-testing-playwright/references/playwright-preflight-sandbox.md](../../.agents/skills/qa-testing-playwright/references/playwright-preflight-sandbox.md)
- [.agents/skills/qa-testing-playwright/references/visual-regression-testing.md](../../.agents/skills/qa-testing-playwright/references/visual-regression-testing.md)

#### .agents/skills/review-anima-live

- [.agents/skills/review-anima-live/SKILL.md](../../.agents/skills/review-anima-live/SKILL.md)

#### .agents/skills/review-anima-live/agents

- [.agents/skills/review-anima-live/agents/openai.yaml](../../.agents/skills/review-anima-live/agents/openai.yaml)

#### .agents/skills/review-anima-live/references

- [.agents/skills/review-anima-live/references/features.md](../../.agents/skills/review-anima-live/references/features.md)

#### .agents/skills/run-anima-live-singing

- [.agents/skills/run-anima-live-singing/SKILL.md](../../.agents/skills/run-anima-live-singing/SKILL.md)

#### .agents/skills/run-anima-live-singing/agents

- [.agents/skills/run-anima-live-singing/agents/openai.yaml](../../.agents/skills/run-anima-live-singing/agents/openai.yaml)

#### .agents/skills/run-anima-live-singing/scripts

- [.agents/skills/run-anima-live-singing/scripts/model_preflight.py](../../.agents/skills/run-anima-live-singing/scripts/model_preflight.py)

#### .agents/skills/simplify

- [.agents/skills/simplify/SKILL.md](../../.agents/skills/simplify/SKILL.md)

#### .agents/skills/simplify/agents

- [.agents/skills/simplify/agents/openai.yaml](../../.agents/skills/simplify/agents/openai.yaml)

#### .agents/skills/simulate-live-danmaku

- [.agents/skills/simulate-live-danmaku/SKILL.md](../../.agents/skills/simulate-live-danmaku/SKILL.md)

#### .agents/skills/simulate-live-danmaku/agents

- [.agents/skills/simulate-live-danmaku/agents/openai.yaml](../../.agents/skills/simulate-live-danmaku/agents/openai.yaml)

#### .agents/skills/simulate-live-danmaku/references

- [.agents/skills/simulate-live-danmaku/references/scenarios.md](../../.agents/skills/simulate-live-danmaku/references/scenarios.md)

#### .agents/skills/simulate-live-danmaku/scripts

- [.agents/skills/simulate-live-danmaku/scripts/danmaku_simulator.py](../../.agents/skills/simulate-live-danmaku/scripts/danmaku_simulator.py)

#### .agents/skills/systematic-debugging

- [.agents/skills/systematic-debugging/condition-based-waiting-example.ts](../../.agents/skills/systematic-debugging/condition-based-waiting-example.ts)
- [.agents/skills/systematic-debugging/condition-based-waiting.md](../../.agents/skills/systematic-debugging/condition-based-waiting.md)
- [.agents/skills/systematic-debugging/defense-in-depth.md](../../.agents/skills/systematic-debugging/defense-in-depth.md)
- [.agents/skills/systematic-debugging/find-polluter.sh](../../.agents/skills/systematic-debugging/find-polluter.sh)
- [.agents/skills/systematic-debugging/root-cause-tracing.md](../../.agents/skills/systematic-debugging/root-cause-tracing.md)
- [.agents/skills/systematic-debugging/SKILL.md](../../.agents/skills/systematic-debugging/SKILL.md)

#### .agents/skills/test-skill-regression

- [.agents/skills/test-skill-regression/SKILL.md](../../.agents/skills/test-skill-regression/SKILL.md)

#### .agents/skills/test-skill-regression/agents

- [.agents/skills/test-skill-regression/agents/openai.yaml](../../.agents/skills/test-skill-regression/agents/openai.yaml)

#### .agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-handoff

- [.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-handoff/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-handoff/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-handoff/result

- [.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-handoff/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-handoff/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-production-acceptance

- [.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-production-acceptance/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-production-acceptance/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-production-acceptance/result

- [.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-production-acceptance/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-production-acceptance/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-smoke-plan

- [.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-smoke-plan/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-smoke-plan/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-smoke-plan/result

- [.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-smoke-plan/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/operate-anima-runtime-smoke-plan/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-fixed-scene-plan

- [.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-fixed-scene-plan/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-fixed-scene-plan/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-fixed-scene-plan/result

- [.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-fixed-scene-plan/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-fixed-scene-plan/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-handoff

- [.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-handoff/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-handoff/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-handoff/result

- [.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-handoff/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-handoff/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-lightweight-acceptance

- [.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-lightweight-acceptance/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-lightweight-acceptance/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-lightweight-acceptance/result

- [.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-lightweight-acceptance/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/review-anima-live-lightweight-acceptance/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/run-anima-live-singing-handoff

- [.agents/skills/test-skill-regression/fixtures/baselines/run-anima-live-singing-handoff/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/run-anima-live-singing-handoff/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/run-anima-live-singing-handoff/result

- [.agents/skills/test-skill-regression/fixtures/baselines/run-anima-live-singing-handoff/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/run-anima-live-singing-handoff/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/simplify-redundant-workflow

- [.agents/skills/test-skill-regression/fixtures/baselines/simplify-redundant-workflow/workflow.md](../../.agents/skills/test-skill-regression/fixtures/baselines/simplify-redundant-workflow/workflow.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/simulate-live-danmaku-smoke-plan

- [.agents/skills/test-skill-regression/fixtures/baselines/simulate-live-danmaku-smoke-plan/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/simulate-live-danmaku-smoke-plan/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/simulate-live-danmaku-smoke-plan/result

- [.agents/skills/test-skill-regression/fixtures/baselines/simulate-live-danmaku-smoke-plan/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/simulate-live-danmaku-smoke-plan/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/validate-anima-daily-plan

- [.agents/skills/test-skill-regression/fixtures/baselines/validate-anima-daily-plan/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/validate-anima-daily-plan/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/validate-anima-daily-plan/result

- [.agents/skills/test-skill-regression/fixtures/baselines/validate-anima-daily-plan/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/validate-anima-daily-plan/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/verify-anima-surfaces-plan

- [.agents/skills/test-skill-regression/fixtures/baselines/verify-anima-surfaces-plan/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/verify-anima-surfaces-plan/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-deterministic

- [.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-deterministic/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-deterministic/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-deterministic/result

- [.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-deterministic/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-deterministic/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-runtime

- [.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-runtime/request.md](../../.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-runtime/request.md)

#### .agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-runtime/result

- [.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-runtime/result/plan.md](../../.agents/skills/test-skill-regression/fixtures/baselines/verify-conversation-continuity-runtime/result/plan.md)

#### .agents/skills/test-skill-regression/fixtures/cases

- [.agents/skills/test-skill-regression/fixtures/cases/operate-anima-runtime-handoff.json](../../.agents/skills/test-skill-regression/fixtures/cases/operate-anima-runtime-handoff.json)
- [.agents/skills/test-skill-regression/fixtures/cases/operate-anima-runtime-production-acceptance.json](../../.agents/skills/test-skill-regression/fixtures/cases/operate-anima-runtime-production-acceptance.json)
- [.agents/skills/test-skill-regression/fixtures/cases/operate-anima-runtime.json](../../.agents/skills/test-skill-regression/fixtures/cases/operate-anima-runtime.json)
- [.agents/skills/test-skill-regression/fixtures/cases/review-anima-live-handoff.json](../../.agents/skills/test-skill-regression/fixtures/cases/review-anima-live-handoff.json)
- [.agents/skills/test-skill-regression/fixtures/cases/review-anima-live-lightweight-acceptance.json](../../.agents/skills/test-skill-regression/fixtures/cases/review-anima-live-lightweight-acceptance.json)
- [.agents/skills/test-skill-regression/fixtures/cases/review-anima-live.json](../../.agents/skills/test-skill-regression/fixtures/cases/review-anima-live.json)
- [.agents/skills/test-skill-regression/fixtures/cases/run-anima-live-singing-handoff.json](../../.agents/skills/test-skill-regression/fixtures/cases/run-anima-live-singing-handoff.json)
- [.agents/skills/test-skill-regression/fixtures/cases/simplify.json](../../.agents/skills/test-skill-regression/fixtures/cases/simplify.json)
- [.agents/skills/test-skill-regression/fixtures/cases/simulate-live-danmaku.json](../../.agents/skills/test-skill-regression/fixtures/cases/simulate-live-danmaku.json)
- [.agents/skills/test-skill-regression/fixtures/cases/validate-anima.json](../../.agents/skills/test-skill-regression/fixtures/cases/validate-anima.json)
- [.agents/skills/test-skill-regression/fixtures/cases/verify-anima-surfaces.json](../../.agents/skills/test-skill-regression/fixtures/cases/verify-anima-surfaces.json)
- [.agents/skills/test-skill-regression/fixtures/cases/verify-conversation-continuity-deterministic.json](../../.agents/skills/test-skill-regression/fixtures/cases/verify-conversation-continuity-deterministic.json)
- [.agents/skills/test-skill-regression/fixtures/cases/verify-conversation-continuity-runtime.json](../../.agents/skills/test-skill-regression/fixtures/cases/verify-conversation-continuity-runtime.json)

#### .agents/skills/test-skill-regression/scripts

- [.agents/skills/test-skill-regression/scripts/compare_runs.py](../../.agents/skills/test-skill-regression/scripts/compare_runs.py)
- [.agents/skills/test-skill-regression/scripts/prepare_case.py](../../.agents/skills/test-skill-regression/scripts/prepare_case.py)
- [.agents/skills/test-skill-regression/scripts/snapshot_tree.py](../../.agents/skills/test-skill-regression/scripts/snapshot_tree.py)

#### .agents/skills/validate-anima

- [.agents/skills/validate-anima/SKILL.md](../../.agents/skills/validate-anima/SKILL.md)

#### .agents/skills/validate-anima/agents

- [.agents/skills/validate-anima/agents/openai.yaml](../../.agents/skills/validate-anima/agents/openai.yaml)

#### .agents/skills/validate-anima/references

- [.agents/skills/validate-anima/references/commands.md](../../.agents/skills/validate-anima/references/commands.md)

#### .agents/skills/verify-anima-surfaces

- [.agents/skills/verify-anima-surfaces/SKILL.md](../../.agents/skills/verify-anima-surfaces/SKILL.md)

#### .agents/skills/verify-anima-surfaces/agents

- [.agents/skills/verify-anima-surfaces/agents/openai.yaml](../../.agents/skills/verify-anima-surfaces/agents/openai.yaml)

#### .agents/skills/verify-anima-surfaces/references

- [.agents/skills/verify-anima-surfaces/references/matrix.md](../../.agents/skills/verify-anima-surfaces/references/matrix.md)

#### .agents/skills/verify-conversation-continuity

- [.agents/skills/verify-conversation-continuity/SKILL.md](../../.agents/skills/verify-conversation-continuity/SKILL.md)

#### .agents/skills/verify-conversation-continuity/agents

- [.agents/skills/verify-conversation-continuity/agents/openai.yaml](../../.agents/skills/verify-conversation-continuity/agents/openai.yaml)

#### .agents/skills/verify-conversation-continuity/references

- [.agents/skills/verify-conversation-continuity/references/contract.md](../../.agents/skills/verify-conversation-continuity/references/contract.md)

#### .agents/skills/verify-conversation-continuity/scripts

- [.agents/skills/verify-conversation-continuity/scripts/run_regression.py](../../.agents/skills/verify-conversation-continuity/scripts/run_regression.py)

### .github

#### .github

- [.github/CODEOWNERS](../../.github/CODEOWNERS)
- [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md)

#### .github/assets

- [.github/assets/readme-cover.webp](../../.github/assets/readme-cover.webp)

#### .github/workflows

- [.github/workflows/deploy-zeabur.yml](../../.github/workflows/deploy-zeabur.yml)
- [.github/workflows/quality.yml](../../.github/workflows/quality.yml)

### .vscode

#### .vscode

- [.vscode/settings.json](../../.vscode/settings.json)

### 根目录

#### 根目录

- [.dockerignore](../../.dockerignore)
- [.env.example](../../.env.example)
- [.env.notifier](../../.env.notifier)
- [.gitattributes](../../.gitattributes)
- [.gitignore](../../.gitignore)
- [.pre-commit-config.yaml](../../.pre-commit-config.yaml)
- [.python-version](../../.python-version)
- [AGENTS.md](../../AGENTS.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [dev-anima.cmd](../../dev-anima.cmd)
- [docker-compose.dev.yml](../../docker-compose.dev.yml)
- [docker-compose.yml](../../docker-compose.yml)
- [Dockerfile](../../Dockerfile)
- [fly.toml](../../fly.toml)
- [LICENSE](../../LICENSE)
- [Makefile](../../Makefile)
- [pyproject.toml](../../pyproject.toml)
- [README.md](../../README.md)
- [README.zh-CN.md](../../README.zh-CN.md)
- [requirements-dev.txt](../../requirements-dev.txt)
- [requirements-local-ai.txt](../../requirements-local-ai.txt)
- [requirements.txt](../../requirements.txt)
- [SECURITY.md](../../SECURITY.md)
- [start-anima.cmd](../../start-anima.cmd)
- [STYLE_GUIDE.md](../../STYLE_GUIDE.md)
- [uv.lock](../../uv.lock)
- [zeabur.json](../../zeabur.json)

### config

#### config

- [config/animetta.yaml](../../config/animetta.yaml)
- [config/bilibili.yaml](../../config/bilibili.yaml)
- [config/host-rvc.yaml](../../config/host-rvc.yaml)
- [config/host-tts.yaml](../../config/host-tts.yaml)
- [config/singing.yaml](../../config/singing.yaml)
- [config/socket-events.json](../../config/socket-events.json)
- [config/tools.yaml](../../config/tools.yaml)

#### config/demo

- [config/demo/golden_scenarios.json](../../config/demo/golden_scenarios.json)

#### config/features

- [config/features/live2d.yaml](../../config/features/live2d.yaml)

#### config/gpt_sovits/evil

- [config/gpt_sovits/evil/tts_infer.yaml](../../config/gpt_sovits/evil/tts_infer.yaml)

#### config/personas

- [config/personas/alice.yaml](../../config/personas/alice.yaml)
- [config/personas/anima.v0.1.yaml](../../config/personas/anima.v0.1.yaml)
- [config/personas/default.yaml](../../config/personas/default.yaml)
- [config/personas/neuro-vtuber.xml](../../config/personas/neuro-vtuber.xml)
- [config/personas/neuro-vtuber.yaml](../../config/personas/neuro-vtuber.yaml)
- [config/personas/README.md](../../config/personas/README.md)
- [config/personas/soujuurou.yaml](../../config/personas/soujuurou.yaml)

#### config/personas/memories

- [config/personas/memories/alice.md](../../config/personas/memories/alice.md)

#### config/personas/voices

- [config/personas/voices/animetta-vivian-reference.wav](../../config/personas/voices/animetta-vivian-reference.wav)
- [config/personas/voices/README.md](../../config/personas/voices/README.md)

#### config/program_scripts

- [config/program_scripts/aura-debut-memory-v1.yaml](../../config/program_scripts/aura-debut-memory-v1.yaml)

### contracts

#### contracts/gamebot/v2

- [contracts/gamebot/v2/schema.json](../../contracts/gamebot/v2/schema.json)
- [contracts/gamebot/v2/schema.sha256](../../contracts/gamebot/v2/schema.sha256)
- [contracts/gamebot/v2/types.d.ts](../../contracts/gamebot/v2/types.d.ts)

#### contracts/gamebot/v2/fixtures

- [contracts/gamebot/v2/fixtures/golden.json](../../contracts/gamebot/v2/fixtures/golden.json)

#### contracts/minecraft/mission/v1

- [contracts/minecraft/mission/v1/schema.json](../../contracts/minecraft/mission/v1/schema.json)
- [contracts/minecraft/mission/v1/schema.sha256](../../contracts/minecraft/mission/v1/schema.sha256)

#### contracts/minecraft/mission/v1/fixtures

- [contracts/minecraft/mission/v1/fixtures/golden.json](../../contracts/minecraft/mission/v1/fixtures/golden.json)

### design-system

#### design-system

- [design-system/all-pages.html](../../design-system/all-pages.html)
- [design-system/brand.html](../../design-system/brand.html)
- [design-system/colors_and_type.css](../../design-system/colors_and_type.css)
- [design-system/colors.html](../../design-system/colors.html)
- [design-system/components.html](../../design-system/components.html)
- [design-system/DEVIATIONS.md](../../design-system/DEVIATIONS.md)
- [design-system/iconography.html](../../design-system/iconography.html)
- [design-system/memory-graph-v2.html](../../design-system/memory-graph-v2.html)
- [design-system/README.md](../../design-system/README.md)
- [design-system/spacing.html](../../design-system/spacing.html)
- [design-system/typography.html](../../design-system/typography.html)
- [design-system/ui-kit.html](../../design-system/ui-kit.html)
- [design-system/USAGE.md](../../design-system/USAGE.md)

#### design-system/assets

- [design-system/assets/avatar.png](../../design-system/assets/avatar.png)
- [design-system/assets/favicon.svg](../../design-system/assets/favicon.svg)

#### design-system/assets/backgrounds

- [design-system/assets/backgrounds/cozy-studio.png](../../design-system/assets/backgrounds/cozy-studio.png)
- [design-system/assets/backgrounds/cyber-city.png](../../design-system/assets/backgrounds/cyber-city.png)
- [design-system/assets/backgrounds/deep-sea.png](../../design-system/assets/backgrounds/deep-sea.png)
- [design-system/assets/backgrounds/default.svg](../../design-system/assets/backgrounds/default.svg)
- [design-system/assets/backgrounds/forest.png](../../design-system/assets/backgrounds/forest.png)
- [design-system/assets/backgrounds/midnight.png](../../design-system/assets/backgrounds/midnight.png)
- [design-system/assets/backgrounds/sakura-night.png](../../design-system/assets/backgrounds/sakura-night.png)
- [design-system/assets/backgrounds/sunset.png](../../design-system/assets/backgrounds/sunset.png)

#### design-system/assets/icons

- [design-system/assets/icons/asr.png](../../design-system/assets/icons/asr.png)
- [design-system/assets/icons/background.png](../../design-system/assets/icons/background.png)
- [design-system/assets/icons/chat.png](../../design-system/assets/icons/chat.png)
- [design-system/assets/icons/controls.png](../../design-system/assets/icons/controls.png)
- [design-system/assets/icons/interrupt.png](../../design-system/assets/icons/interrupt.png)
- [design-system/assets/icons/live2d.png](../../design-system/assets/icons/live2d.png)
- [design-system/assets/icons/llm.png](../../design-system/assets/icons/llm.png)
- [design-system/assets/icons/memory.png](../../design-system/assets/icons/memory.png)
- [design-system/assets/icons/persona.png](../../design-system/assets/icons/persona.png)
- [design-system/assets/icons/tts.png](../../design-system/assets/icons/tts.png)
- [design-system/assets/icons/vad.png](../../design-system/assets/icons/vad.png)

### docker

#### docker

- [docker/build-frontend.sh](../../docker/build-frontend.sh)
- [docker/entrypoint.sh](../../docker/entrypoint.sh)
- [docker/nginx.conf](../../docker/nginx.conf)

#### docker/mcp-filesystem

- [docker/mcp-filesystem/Dockerfile](../../docker/mcp-filesystem/Dockerfile)

#### docker/minecraft-server/client-mods

- [docker/minecraft-server/client-mods/fabric-api-0.102.0+1.21.jar](../../docker/minecraft-server/client-mods/fabric-api-0.102.0%2B1.21.jar)
- [docker/minecraft-server/client-mods/spectatorplus-fabric-1.2.1-mc1.21.jar](../../docker/minecraft-server/client-mods/spectatorplus-fabric-1.2.1-mc1.21.jar)

### docs

#### docs

- [docs/bounded-execution-feedback.md](../../docs/bounded-execution-feedback.md)
- [docs/persona-training-lab-runtime-contract.md](../../docs/persona-training-lab-runtime-contract.md)
- [docs/README.md](../../docs/README.md)
- [docs/risk-log.md](../../docs/risk-log.md)
- [docs/roadmap.md](../../docs/roadmap.md)

#### docs/adrs

- [docs/adrs/ADR-001-langgraph-over-eventbus.md](../../docs/adrs/ADR-001-langgraph-over-eventbus.md)
- [docs/adrs/ADR-002-hybrid-search.md](../../docs/adrs/ADR-002-hybrid-search.md)
- [docs/adrs/ADR-003-plugin-architecture.md](../../docs/adrs/ADR-003-plugin-architecture.md)
- [docs/adrs/ADR-004-streaming-response.md](../../docs/adrs/ADR-004-streaming-response.md)
- [docs/adrs/ADR-005-wiki-memory.md](../../docs/adrs/ADR-005-wiki-memory.md)
- [docs/adrs/ADR-006-observability-stack.md](../../docs/adrs/ADR-006-observability-stack.md)
- [docs/adrs/ADR-007-wiki-memory-extensions.md](../../docs/adrs/ADR-007-wiki-memory-extensions.md)
- [docs/adrs/ADR-008-mcp-bridge.md](../../docs/adrs/ADR-008-mcp-bridge.md)
- [docs/adrs/ADR-009-live2d-expression.md](../../docs/adrs/ADR-009-live2d-expression.md)
- [docs/adrs/ADR-010-bilibili-meme-collection.md](../../docs/adrs/ADR-010-bilibili-meme-collection.md)
- [docs/adrs/ADR-011-realtime-audio-pipeline.md](../../docs/adrs/ADR-011-realtime-audio-pipeline.md)
- [docs/adrs/ADR-012-sqlite-command-inbox.md](../../docs/adrs/ADR-012-sqlite-command-inbox.md)
- [docs/adrs/ADR-013-unidirectional-module-boundaries.md](../../docs/adrs/ADR-013-unidirectional-module-boundaries.md)
- [docs/adrs/AGENTS.md](../../docs/adrs/AGENTS.md)
- [docs/adrs/README.md](../../docs/adrs/README.md)

#### docs/architecture

- [docs/architecture/file-index.md](../../docs/architecture/file-index.md)
- [docs/architecture/gamebot-v2-protocol-matrix.md](../../docs/architecture/gamebot-v2-protocol-matrix.md)
- [docs/architecture/minecraft-voyager-control-plane-inventory.md](../../docs/architecture/minecraft-voyager-control-plane-inventory.md)
- [docs/architecture/module-map.md](../../docs/architecture/module-map.md)
- [docs/architecture/overview.md](../../docs/architecture/overview.md)
- [docs/architecture/patterns.md](../../docs/architecture/patterns.md)

#### docs/demo

- [docs/demo/interview-demo.md](../../docs/demo/interview-demo.md)
- [docs/demo/interview-qa.md](../../docs/demo/interview-qa.md)

#### docs/deployment

- [docs/deployment/docker.md](../../docs/deployment/docker.md)
- [docs/deployment/zeabur.md](../../docs/deployment/zeabur.md)

#### docs/development

- [docs/development/ai-ui-workflow.md](../../docs/development/ai-ui-workflow.md)
- [docs/development/earth-exploration-plan.md](../../docs/development/earth-exploration-plan.md)
- [docs/development/earth-exploration-verification.md](../../docs/development/earth-exploration-verification.md)
- [docs/development/earth-prototype.md](../../docs/development/earth-prototype.md)
- [docs/development/gpt-sovits-rtx5090-setup.md](../../docs/development/gpt-sovits-rtx5090-setup.md)
- [docs/development/minecraft-bot-architecture.md](../../docs/development/minecraft-bot-architecture.md)
- [docs/development/project-health.md](../../docs/development/project-health.md)
- [docs/development/runtime-config-reload.md](../../docs/development/runtime-config-reload.md)
- [docs/development/rvc-training-guide.md](../../docs/development/rvc-training-guide.md)
- [docs/development/streaming-interaction-patterns.md](../../docs/development/streaming-interaction-patterns.md)
- [docs/development/testing.md](../../docs/development/testing.md)

#### docs/development/earth-evidence

- [docs/development/earth-evidence/formal-acceptance.json](../../docs/development/earth-evidence/formal-acceptance.json)
- [docs/development/earth-evidence/formal-manifest.json](../../docs/development/earth-evidence/formal-manifest.json)
- [docs/development/earth-evidence/formal-map-timing.json](../../docs/development/earth-evidence/formal-map-timing.json)
- [docs/development/earth-evidence/manifest.json](../../docs/development/earth-evidence/manifest.json)
- [docs/development/earth-evidence/perf-baseline-isolated-raw.json](../../docs/development/earth-evidence/perf-baseline-isolated-raw.json)
- [docs/development/earth-evidence/perf-baseline-resume-raw.json](../../docs/development/earth-evidence/perf-baseline-resume-raw.json)
- [docs/development/earth-evidence/perf-post-renderer-raw.json](../../docs/development/earth-evidence/perf-post-renderer-raw.json)
- [docs/development/earth-evidence/perf-post-renderer-resume-raw.json](../../docs/development/earth-evidence/perf-post-renderer-resume-raw.json)
- [docs/development/earth-evidence/README.md](../../docs/development/earth-evidence/README.md)

#### docs/minecraft

- [docs/minecraft/client-viewer.md](../../docs/minecraft/client-viewer.md)

#### docs/performance

- [docs/performance/startup-2026-09-12.md](../../docs/performance/startup-2026-09-12.md)
- [docs/performance/startup-build-prediction-2026-09-12.json](../../docs/performance/startup-build-prediction-2026-09-12.json)
- [docs/performance/startup-cold-prediction-2026-09-12.json](../../docs/performance/startup-cold-prediction-2026-09-12.json)
- [docs/performance/startup-comparison-2026-09-12.svg](../../docs/performance/startup-comparison-2026-09-12.svg)
- [docs/performance/startup-predictions-2026-09-12.json](../../docs/performance/startup-predictions-2026-09-12.json)
- [docs/performance/startup-results-2026-09-12.csv](../../docs/performance/startup-results-2026-09-12.csv)
- [docs/performance/startup-results-2026-09-12.json](../../docs/performance/startup-results-2026-09-12.json)

#### docs/performance/cold-storage-2026-09-13

- [docs/performance/cold-storage-2026-09-13/build-results.csv](../../docs/performance/cold-storage-2026-09-13/build-results.csv)
- [docs/performance/cold-storage-2026-09-13/build-results.json](../../docs/performance/cold-storage-2026-09-13/build-results.json)
- [docs/performance/cold-storage-2026-09-13/cold-build-comparison.png](../../docs/performance/cold-storage-2026-09-13/cold-build-comparison.png)
- [docs/performance/cold-storage-2026-09-13/cold-build-comparison.svg](../../docs/performance/cold-storage-2026-09-13/cold-build-comparison.svg)
- [docs/performance/cold-storage-2026-09-13/environment.json](../../docs/performance/cold-storage-2026-09-13/environment.json)
- [docs/performance/cold-storage-2026-09-13/model-load-comparison.png](../../docs/performance/cold-storage-2026-09-13/model-load-comparison.png)
- [docs/performance/cold-storage-2026-09-13/model-load-comparison.svg](../../docs/performance/cold-storage-2026-09-13/model-load-comparison.svg)
- [docs/performance/cold-storage-2026-09-13/model-predictions.json](../../docs/performance/cold-storage-2026-09-13/model-predictions.json)
- [docs/performance/cold-storage-2026-09-13/model-results.csv](../../docs/performance/cold-storage-2026-09-13/model-results.csv)
- [docs/performance/cold-storage-2026-09-13/model-results.json](../../docs/performance/cold-storage-2026-09-13/model-results.json)
- [docs/performance/cold-storage-2026-09-13/predictions.json](../../docs/performance/cold-storage-2026-09-13/predictions.json)
- [docs/performance/cold-storage-2026-09-13/read-results.csv](../../docs/performance/cold-storage-2026-09-13/read-results.csv)
- [docs/performance/cold-storage-2026-09-13/read-results.json](../../docs/performance/cold-storage-2026-09-13/read-results.json)
- [docs/performance/cold-storage-2026-09-13/README.md](../../docs/performance/cold-storage-2026-09-13/README.md)
- [docs/performance/cold-storage-2026-09-13/unbuffered-read-comparison.png](../../docs/performance/cold-storage-2026-09-13/unbuffered-read-comparison.png)
- [docs/performance/cold-storage-2026-09-13/unbuffered-read-comparison.svg](../../docs/performance/cold-storage-2026-09-13/unbuffered-read-comparison.svg)

#### docs/performance/cold-storage-2026-09-13/raw

- [docs/performance/cold-storage-2026-09-13/raw/apt-stage-analysis.json](../../docs/performance/cold-storage-2026-09-13/raw/apt-stage-analysis.json)
- [docs/performance/cold-storage-2026-09-13/raw/b1-telemetry.csv](../../docs/performance/cold-storage-2026-09-13/raw/b1-telemetry.csv)
- [docs/performance/cold-storage-2026-09-13/raw/b1.json](../../docs/performance/cold-storage-2026-09-13/raw/b1.json)
- [docs/performance/cold-storage-2026-09-13/raw/b2-telemetry.csv](../../docs/performance/cold-storage-2026-09-13/raw/b2-telemetry.csv)
- [docs/performance/cold-storage-2026-09-13/raw/b2.json](../../docs/performance/cold-storage-2026-09-13/raw/b2.json)
- [docs/performance/cold-storage-2026-09-13/raw/b3-telemetry.csv](../../docs/performance/cold-storage-2026-09-13/raw/b3-telemetry.csv)
- [docs/performance/cold-storage-2026-09-13/raw/b3.json](../../docs/performance/cold-storage-2026-09-13/raw/b3.json)
- [docs/performance/cold-storage-2026-09-13/raw/c1-telemetry.csv](../../docs/performance/cold-storage-2026-09-13/raw/c1-telemetry.csv)
- [docs/performance/cold-storage-2026-09-13/raw/c1.json](../../docs/performance/cold-storage-2026-09-13/raw/c1.json)
- [docs/performance/cold-storage-2026-09-13/raw/c2-telemetry.csv](../../docs/performance/cold-storage-2026-09-13/raw/c2-telemetry.csv)
- [docs/performance/cold-storage-2026-09-13/raw/c2.json](../../docs/performance/cold-storage-2026-09-13/raw/c2.json)
- [docs/performance/cold-storage-2026-09-13/raw/c3-telemetry.csv](../../docs/performance/cold-storage-2026-09-13/raw/c3-telemetry.csv)
- [docs/performance/cold-storage-2026-09-13/raw/c3.json](../../docs/performance/cold-storage-2026-09-13/raw/c3.json)
- [docs/performance/cold-storage-2026-09-13/raw/c4-telemetry.csv](../../docs/performance/cold-storage-2026-09-13/raw/c4-telemetry.csv)
- [docs/performance/cold-storage-2026-09-13/raw/c4.json](../../docs/performance/cold-storage-2026-09-13/raw/c4.json)
- [docs/performance/cold-storage-2026-09-13/raw/desktop-force-stop.json](../../docs/performance/cold-storage-2026-09-13/raw/desktop-force-stop.json)
- [docs/performance/cold-storage-2026-09-13/raw/final-desktop-recovery.json](../../docs/performance/cold-storage-2026-09-13/raw/final-desktop-recovery.json)
- [docs/performance/cold-storage-2026-09-13/raw/final-quality-summary.json](../../docs/performance/cold-storage-2026-09-13/raw/final-quality-summary.json)
- [docs/performance/cold-storage-2026-09-13/raw/final-smoke-summary.json](../../docs/performance/cold-storage-2026-09-13/raw/final-smoke-summary.json)
- [docs/performance/cold-storage-2026-09-13/raw/ipc-recovery.json](../../docs/performance/cold-storage-2026-09-13/raw/ipc-recovery.json)
- [docs/performance/cold-storage-2026-09-13/raw/migration-attempt-01.json](../../docs/performance/cold-storage-2026-09-13/raw/migration-attempt-01.json)
- [docs/performance/cold-storage-2026-09-13/raw/migration-attempt-02.json](../../docs/performance/cold-storage-2026-09-13/raw/migration-attempt-02.json)
- [docs/performance/cold-storage-2026-09-13/raw/migration-backup.json](../../docs/performance/cold-storage-2026-09-13/raw/migration-backup.json)
- [docs/performance/cold-storage-2026-09-13/raw/migration-space-gate.json](../../docs/performance/cold-storage-2026-09-13/raw/migration-space-gate.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-copy-manifest.json](../../docs/performance/cold-storage-2026-09-13/raw/model-copy-manifest.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-hdd-qwen.json](../../docs/performance/cold-storage-2026-09-13/raw/model-hdd-qwen.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-hdd-rvc.json](../../docs/performance/cold-storage-2026-09-13/raw/model-hdd-rvc.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-input-file-sizes.json](../../docs/performance/cold-storage-2026-09-13/raw/model-input-file-sizes.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-measure-driver.zip](../../docs/performance/cold-storage-2026-09-13/raw/model-measure-driver.zip)
- [docs/performance/cold-storage-2026-09-13/raw/model-measurement-frozen.json](../../docs/performance/cold-storage-2026-09-13/raw/model-measurement-frozen.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-measurement-refrozen.json](../../docs/performance/cold-storage-2026-09-13/raw/model-measurement-refrozen.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-paths-original.json](../../docs/performance/cold-storage-2026-09-13/raw/model-paths-original.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-restoration-verified.json](../../docs/performance/cold-storage-2026-09-13/raw/model-restoration-verified.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-ssd-qwen-v2.json](../../docs/performance/cold-storage-2026-09-13/raw/model-ssd-qwen-v2.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-ssd-qwen.json](../../docs/performance/cold-storage-2026-09-13/raw/model-ssd-qwen.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-ssd-rvc-v2-continuation.json](../../docs/performance/cold-storage-2026-09-13/raw/model-ssd-rvc-v2-continuation.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-ssd-rvc-v2.json](../../docs/performance/cold-storage-2026-09-13/raw/model-ssd-rvc-v2.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-ssd-rvc.json](../../docs/performance/cold-storage-2026-09-13/raw/model-ssd-rvc.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-unbuffered-hdd.json](../../docs/performance/cold-storage-2026-09-13/raw/model-unbuffered-hdd.json)
- [docs/performance/cold-storage-2026-09-13/raw/model-unbuffered-ssd.json](../../docs/performance/cold-storage-2026-09-13/raw/model-unbuffered-ssd.json)
- [docs/performance/cold-storage-2026-09-13/raw/no-gcc-probe.json](../../docs/performance/cold-storage-2026-09-13/raw/no-gcc-probe.json)
- [docs/performance/cold-storage-2026-09-13/raw/preparation-failure.json](../../docs/performance/cold-storage-2026-09-13/raw/preparation-failure.json)
- [docs/performance/cold-storage-2026-09-13/raw/rvc-junction-restored.json](../../docs/performance/cold-storage-2026-09-13/raw/rvc-junction-restored.json)

#### docs/performance/cold-storage-2026-09-13/raw/final

- [docs/performance/cold-storage-2026-09-13/raw/final/dev-down.json](../../docs/performance/cold-storage-2026-09-13/raw/final/dev-down.json)
- [docs/performance/cold-storage-2026-09-13/raw/final/dev-up.json](../../docs/performance/cold-storage-2026-09-13/raw/final/dev-up.json)
- [docs/performance/cold-storage-2026-09-13/raw/final/formal-down.json](../../docs/performance/cold-storage-2026-09-13/raw/final/formal-down.json)
- [docs/performance/cold-storage-2026-09-13/raw/final/formal-restore.json](../../docs/performance/cold-storage-2026-09-13/raw/final/formal-restore.json)
- [docs/performance/cold-storage-2026-09-13/raw/final/formal-up.json](../../docs/performance/cold-storage-2026-09-13/raw/final/formal-up.json)
- [docs/performance/cold-storage-2026-09-13/raw/final/hosts-after-formal-down.json](../../docs/performance/cold-storage-2026-09-13/raw/final/hosts-after-formal-down.json)

#### docs/reference

- [docs/reference/backend-api.md](../../docs/reference/backend-api.md)
- [docs/reference/public-api.md](../../docs/reference/public-api.md)
- [docs/reference/rag-evaluation-report.md](../../docs/reference/rag-evaluation-report.md)
- [docs/reference/socket-api.md](../../docs/reference/socket-api.md)
- [docs/reference/tools.md](../../docs/reference/tools.md)

#### docs/retrospective

- [docs/retrospective/2026-07.md](../../docs/retrospective/2026-07.md)

#### docs/runbooks

- [docs/runbooks/livestream-replay-evaluation.md](../../docs/runbooks/livestream-replay-evaluation.md)

### evaluations

#### evaluations

- [evaluations/AGENTS.md](../../evaluations/AGENTS.md)

#### evaluations/agent

- [evaluations/agent/__init__.py](../../evaluations/agent/__init__.py)
- [evaluations/agent/__main__.py](../../evaluations/agent/__main__.py)
- [evaluations/agent/evaluator.py](../../evaluations/agent/evaluator.py)
- [evaluations/agent/models.py](../../evaluations/agent/models.py)

#### evaluations/agent/datasets

- [evaluations/agent/datasets/baseline-v1.json](../../evaluations/agent/datasets/baseline-v1.json)
- [evaluations/agent/datasets/v1.jsonl](../../evaluations/agent/datasets/v1.jsonl)

#### evaluations/livestream

- [evaluations/livestream/__init__.py](../../evaluations/livestream/__init__.py)
- [evaluations/livestream/__main__.py](../../evaluations/livestream/__main__.py)
- [evaluations/livestream/capture.py](../../evaluations/livestream/capture.py)
- [evaluations/livestream/cleaning_evidence.py](../../evaluations/livestream/cleaning_evidence.py)
- [evaluations/livestream/cleaning.py](../../evaluations/livestream/cleaning.py)
- [evaluations/livestream/cli.py](../../evaluations/livestream/cli.py)
- [evaluations/livestream/dataset.py](../../evaluations/livestream/dataset.py)
- [evaluations/livestream/enrichment.py](../../evaluations/livestream/enrichment.py)
- [evaluations/livestream/judge.py](../../evaluations/livestream/judge.py)
- [evaluations/livestream/pipeline.py](../../evaluations/livestream/pipeline.py)
- [evaluations/livestream/reporting.py](../../evaluations/livestream/reporting.py)
- [evaluations/livestream/runner.py](../../evaluations/livestream/runner.py)
- [evaluations/livestream/semantic.py](../../evaluations/livestream/semantic.py)
- [evaluations/livestream/socket_processor.py](../../evaluations/livestream/socket_processor.py)
- [evaluations/livestream/twitch_vod.py](../../evaluations/livestream/twitch_vod.py)

#### evaluations/rag

- [evaluations/rag/__init__.py](../../evaluations/rag/__init__.py)
- [evaluations/rag/configs.yaml](../../evaluations/rag/configs.yaml)
- [evaluations/rag/dataset_builder.py](../../evaluations/rag/dataset_builder.py)
- [evaluations/rag/dataset.jsonl](../../evaluations/rag/dataset.jsonl)
- [evaluations/rag/metrics.py](../../evaluations/rag/metrics.py)
- [evaluations/rag/README.md](../../evaluations/rag/README.md)
- [evaluations/rag/reporter.py](../../evaluations/rag/reporter.py)
- [evaluations/rag/runner.py](../../evaluations/rag/runner.py)

### frontend

#### frontend

- [frontend/.env.production](../../frontend/.env.production)
- [frontend/.npmrc](../../frontend/.npmrc)
- [frontend/.prettierignore](../../frontend/.prettierignore)
- [frontend/.prettierrc.json](../../frontend/.prettierrc.json)
- [frontend/AGENTS.md](../../frontend/AGENTS.md)
- [frontend/earth-prototype.html](../../frontend/earth-prototype.html)
- [frontend/electron-builder.json](../../frontend/electron-builder.json)
- [frontend/eslint.config.js](../../frontend/eslint.config.js)
- [frontend/index.html](../../frontend/index.html)
- [frontend/knip.json](../../frontend/knip.json)
- [frontend/live.html](../../frontend/live.html)
- [frontend/minecraft-gameplay.html](../../frontend/minecraft-gameplay.html)
- [frontend/package.json](../../frontend/package.json)
- [frontend/pnpm-lock.yaml](../../frontend/pnpm-lock.yaml)
- [frontend/pnpm-workspace.yaml](../../frontend/pnpm-workspace.yaml)
- [frontend/pnpm.approve.json](../../frontend/pnpm.approve.json)
- [frontend/smoke-test.mjs](../../frontend/smoke-test.mjs)
- [frontend/start-electron-dev.bat](../../frontend/start-electron-dev.bat)
- [frontend/start-electron-dev.ps1](../../frontend/start-electron-dev.ps1)
- [frontend/start-live-stream.bat](../../frontend/start-live-stream.bat)
- [frontend/streaming-tts-smoke.mjs](../../frontend/streaming-tts-smoke.mjs)
- [frontend/tsconfig.json](../../frontend/tsconfig.json)
- [frontend/tsconfig.node.json](../../frontend/tsconfig.node.json)
- [frontend/tsconfig.review.json](../../frontend/tsconfig.review.json)
- [frontend/uno.config.ts](../../frontend/uno.config.ts)
- [frontend/vite.config.ts](../../frontend/vite.config.ts)
- [frontend/vitest.config.ts](../../frontend/vitest.config.ts)

#### frontend/.openai

- [frontend/.openai/hosting.json](../../frontend/.openai/hosting.json)

#### frontend/electron

- [frontend/electron/main.cjs](../../frontend/electron/main.cjs)
- [frontend/electron/preload.cjs](../../frontend/electron/preload.cjs)

#### frontend/public

- [frontend/public/favicon.svg](../../frontend/public/favicon.svg)
- [frontend/public/LIVE-STREAM-TEST.md](../../frontend/public/LIVE-STREAM-TEST.md)
- [frontend/public/test-danmaku-data.json](../../frontend/public/test-danmaku-data.json)

#### frontend/public/backgrounds

- [frontend/public/backgrounds/落日.png](../../frontend/public/backgrounds/%E8%90%BD%E6%97%A5.png)
- [frontend/public/backgrounds/赛博都市.png](../../frontend/public/backgrounds/%E8%B5%9B%E5%8D%9A%E9%83%BD%E5%B8%82.png)
- [frontend/public/backgrounds/森林.png](../../frontend/public/backgrounds/%E6%A3%AE%E6%9E%97.png)
- [frontend/public/backgrounds/深海.png](../../frontend/public/backgrounds/%E6%B7%B1%E6%B5%B7.png)
- [frontend/public/backgrounds/温馨直播室.png](../../frontend/public/backgrounds/%E6%B8%A9%E9%A6%A8%E7%9B%B4%E6%92%AD%E5%AE%A4.png)
- [frontend/public/backgrounds/午夜.png](../../frontend/public/backgrounds/%E5%8D%88%E5%A4%9C.png)
- [frontend/public/backgrounds/樱花夜.png](../../frontend/public/backgrounds/%E6%A8%B1%E8%8A%B1%E5%A4%9C.png)

#### frontend/public/backgrounds/vertical

- [frontend/public/backgrounds/vertical/README.md](../../frontend/public/backgrounds/vertical/README.md)

#### frontend/public/live2d

- [frontend/public/live2d/live2dcubismcore.min.js](../../frontend/public/live2d/live2dcubismcore.min.js)

#### frontend/public/live2d/haru

- [frontend/public/live2d/haru/haru_greeter_t03.moc3](../../frontend/public/live2d/haru/haru_greeter_t03.moc3)
- [frontend/public/live2d/haru/haru_greeter_t03.model3.json](../../frontend/public/live2d/haru/haru_greeter_t03.model3.json)
- [frontend/public/live2d/haru/haru_greeter_t03.physics3.json](../../frontend/public/live2d/haru/haru_greeter_t03.physics3.json)
- [frontend/public/live2d/haru/haru_greeter_t03.pose3.json](../../frontend/public/live2d/haru/haru_greeter_t03.pose3.json)

#### frontend/public/live2d/haru/expressions

- [frontend/public/live2d/haru/expressions/F01.exp3.json](../../frontend/public/live2d/haru/expressions/F01.exp3.json)
- [frontend/public/live2d/haru/expressions/F02.exp3.json](../../frontend/public/live2d/haru/expressions/F02.exp3.json)
- [frontend/public/live2d/haru/expressions/F03.exp3.json](../../frontend/public/live2d/haru/expressions/F03.exp3.json)
- [frontend/public/live2d/haru/expressions/F04.exp3.json](../../frontend/public/live2d/haru/expressions/F04.exp3.json)
- [frontend/public/live2d/haru/expressions/F05.exp3.json](../../frontend/public/live2d/haru/expressions/F05.exp3.json)
- [frontend/public/live2d/haru/expressions/F06.exp3.json](../../frontend/public/live2d/haru/expressions/F06.exp3.json)
- [frontend/public/live2d/haru/expressions/F07.exp3.json](../../frontend/public/live2d/haru/expressions/F07.exp3.json)
- [frontend/public/live2d/haru/expressions/F08.exp3.json](../../frontend/public/live2d/haru/expressions/F08.exp3.json)

#### frontend/public/live2d/haru/haru_greeter_t03.2048

- [frontend/public/live2d/haru/haru_greeter_t03.2048/texture_00.png](../../frontend/public/live2d/haru/haru_greeter_t03.2048/texture_00.png)
- [frontend/public/live2d/haru/haru_greeter_t03.2048/texture_01.png](../../frontend/public/live2d/haru/haru_greeter_t03.2048/texture_01.png)

#### frontend/public/live2d/haru/motion

- [frontend/public/live2d/haru/motion/haru_g_idle.motion3.json](../../frontend/public/live2d/haru/motion/haru_g_idle.motion3.json)
- [frontend/public/live2d/haru/motion/haru_g_m05.motion3.json](../../frontend/public/live2d/haru/motion/haru_g_m05.motion3.json)
- [frontend/public/live2d/haru/motion/haru_g_m07.motion3.json](../../frontend/public/live2d/haru/motion/haru_g_m07.motion3.json)
- [frontend/public/live2d/haru/motion/haru_g_m14.motion3.json](../../frontend/public/live2d/haru/motion/haru_g_m14.motion3.json)
- [frontend/public/live2d/haru/motion/haru_g_m15.motion3.json](../../frontend/public/live2d/haru/motion/haru_g_m15.motion3.json)

#### frontend/public/live2d/hiyori

- [frontend/public/live2d/hiyori/Hiyori.cdi3.json](../../frontend/public/live2d/hiyori/Hiyori.cdi3.json)
- [frontend/public/live2d/hiyori/Hiyori.moc3](../../frontend/public/live2d/hiyori/Hiyori.moc3)
- [frontend/public/live2d/hiyori/Hiyori.model3.json](../../frontend/public/live2d/hiyori/Hiyori.model3.json)
- [frontend/public/live2d/hiyori/Hiyori.physics3.json](../../frontend/public/live2d/hiyori/Hiyori.physics3.json)
- [frontend/public/live2d/hiyori/Hiyori.pose3.json](../../frontend/public/live2d/hiyori/Hiyori.pose3.json)
- [frontend/public/live2d/hiyori/Hiyori.userdata3.json](../../frontend/public/live2d/hiyori/Hiyori.userdata3.json)

#### frontend/public/live2d/hiyori/Hiyori.2048

- [frontend/public/live2d/hiyori/Hiyori.2048/texture_00.png](../../frontend/public/live2d/hiyori/Hiyori.2048/texture_00.png)
- [frontend/public/live2d/hiyori/Hiyori.2048/texture_01.png](../../frontend/public/live2d/hiyori/Hiyori.2048/texture_01.png)

#### frontend/public/live2d/hiyori/motions

- [frontend/public/live2d/hiyori/motions/Hiyori_m01.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m01.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m02.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m02.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m03.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m03.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m04.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m04.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m05.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m05.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m06.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m06.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m07.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m07.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m08.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m08.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m09.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m09.motion3.json)
- [frontend/public/live2d/hiyori/motions/Hiyori_m10.motion3.json](../../frontend/public/live2d/hiyori/motions/Hiyori_m10.motion3.json)

#### frontend/public/live2d/mao

- [frontend/public/live2d/mao/ASSET_LICENSE.md](../../frontend/public/live2d/mao/ASSET_LICENSE.md)
- [frontend/public/live2d/mao/Mao.cdi3.json](../../frontend/public/live2d/mao/Mao.cdi3.json)
- [frontend/public/live2d/mao/Mao.moc3](../../frontend/public/live2d/mao/Mao.moc3)
- [frontend/public/live2d/mao/Mao.model3.json](../../frontend/public/live2d/mao/Mao.model3.json)
- [frontend/public/live2d/mao/Mao.physics3.json](../../frontend/public/live2d/mao/Mao.physics3.json)
- [frontend/public/live2d/mao/Mao.pose3.json](../../frontend/public/live2d/mao/Mao.pose3.json)

#### frontend/public/live2d/mao/expressions

- [frontend/public/live2d/mao/expressions/exp_01.exp3.json](../../frontend/public/live2d/mao/expressions/exp_01.exp3.json)
- [frontend/public/live2d/mao/expressions/exp_02.exp3.json](../../frontend/public/live2d/mao/expressions/exp_02.exp3.json)
- [frontend/public/live2d/mao/expressions/exp_03.exp3.json](../../frontend/public/live2d/mao/expressions/exp_03.exp3.json)
- [frontend/public/live2d/mao/expressions/exp_04.exp3.json](../../frontend/public/live2d/mao/expressions/exp_04.exp3.json)
- [frontend/public/live2d/mao/expressions/exp_05.exp3.json](../../frontend/public/live2d/mao/expressions/exp_05.exp3.json)
- [frontend/public/live2d/mao/expressions/exp_06.exp3.json](../../frontend/public/live2d/mao/expressions/exp_06.exp3.json)
- [frontend/public/live2d/mao/expressions/exp_07.exp3.json](../../frontend/public/live2d/mao/expressions/exp_07.exp3.json)
- [frontend/public/live2d/mao/expressions/exp_08.exp3.json](../../frontend/public/live2d/mao/expressions/exp_08.exp3.json)

#### frontend/public/live2d/mao/Mao.2048

- [frontend/public/live2d/mao/Mao.2048/texture_00.png](../../frontend/public/live2d/mao/Mao.2048/texture_00.png)

#### frontend/public/live2d/mao/motions

- [frontend/public/live2d/mao/motions/mtn_01.motion3.json](../../frontend/public/live2d/mao/motions/mtn_01.motion3.json)
- [frontend/public/live2d/mao/motions/mtn_02.motion3.json](../../frontend/public/live2d/mao/motions/mtn_02.motion3.json)
- [frontend/public/live2d/mao/motions/mtn_03.motion3.json](../../frontend/public/live2d/mao/motions/mtn_03.motion3.json)
- [frontend/public/live2d/mao/motions/mtn_04.motion3.json](../../frontend/public/live2d/mao/motions/mtn_04.motion3.json)
- [frontend/public/live2d/mao/motions/sample_01.motion3.json](../../frontend/public/live2d/mao/motions/sample_01.motion3.json)
- [frontend/public/live2d/mao/motions/special_01.motion3.json](../../frontend/public/live2d/mao/motions/special_01.motion3.json)
- [frontend/public/live2d/mao/motions/special_02.motion3.json](../../frontend/public/live2d/mao/motions/special_02.motion3.json)
- [frontend/public/live2d/mao/motions/special_03.motion3.json](../../frontend/public/live2d/mao/motions/special_03.motion3.json)

#### frontend/scripts

- [frontend/scripts/assert-live-build.mjs](../../frontend/scripts/assert-live-build.mjs)
- [frontend/scripts/benchmark-startup.mjs](../../frontend/scripts/benchmark-startup.mjs)
- [frontend/scripts/earth-assets.ts](../../frontend/scripts/earth-assets.ts)
- [frontend/scripts/live-singing-smoke.ts](../../frontend/scripts/live-singing-smoke.ts)
- [frontend/scripts/package-sites-worker.mjs](../../frontend/scripts/package-sites-worker.mjs)

#### frontend/scripts/review

- [frontend/scripts/review/assertions.ts](../../frontend/scripts/review/assertions.ts)
- [frontend/scripts/review/browser.ts](../../frontend/scripts/review/browser.ts)
- [frontend/scripts/review/cli.ts](../../frontend/scripts/review/cli.ts)
- [frontend/scripts/review/evidence.ts](../../frontend/scripts/review/evidence.ts)
- [frontend/scripts/review/image-compare.ts](../../frontend/scripts/review/image-compare.ts)
- [frontend/scripts/review/lifecycle.ts](../../frontend/scripts/review/lifecycle.ts)
- [frontend/scripts/review/minecraft-harness-lease.ts](../../frontend/scripts/review/minecraft-harness-lease.ts)
- [frontend/scripts/review/minecraft-obs.ts](../../frontend/scripts/review/minecraft-obs.ts)
- [frontend/scripts/review/minecraft-review-client.ts](../../frontend/scripts/review/minecraft-review-client.ts)
- [frontend/scripts/review/obs.ts](../../frontend/scripts/review/obs.ts)
- [frontend/scripts/review/options.ts](../../frontend/scripts/review/options.ts)
- [frontend/scripts/review/orchestrator.ts](../../frontend/scripts/review/orchestrator.ts)
- [frontend/scripts/review/policies.ts](../../frontend/scripts/review/policies.ts)
- [frontend/scripts/review/prune.ts](../../frontend/scripts/review/prune.ts)
- [frontend/scripts/review/registry.ts](../../frontend/scripts/review/registry.ts)
- [frontend/scripts/review/server-lease.ts](../../frontend/scripts/review/server-lease.ts)
- [frontend/scripts/review/tts-harness-contract.ts](../../frontend/scripts/review/tts-harness-contract.ts)
- [frontend/scripts/review/tts-harness-lease.ts](../../frontend/scripts/review/tts-harness-lease.ts)
- [frontend/scripts/review/tts-review-client.ts](../../frontend/scripts/review/tts-review-client.ts)

#### frontend/scripts/review/plugins

- [frontend/scripts/review/plugins/live.ts](../../frontend/scripts/review/plugins/live.ts)
- [frontend/scripts/review/plugins/live2d-performance.ts](../../frontend/scripts/review/plugins/live2d-performance.ts)
- [frontend/scripts/review/plugins/minecraft-gameplay.ts](../../frontend/scripts/review/plugins/minecraft-gameplay.ts)
- [frontend/scripts/review/plugins/tts-failover.ts](../../frontend/scripts/review/plugins/tts-failover.ts)

#### frontend/src

- [frontend/src/App.vue](../../frontend/src/App.vue)
- [frontend/src/env.d.ts](../../frontend/src/env.d.ts)
- [frontend/src/main.ts](../../frontend/src/main.ts)
- [frontend/src/smoke.test.ts](../../frontend/src/smoke.test.ts)

#### frontend/src/__tests__

- [frontend/src/__tests__/App.smoke.test.ts](../../frontend/src/__tests__/App.smoke.test.ts)
- [frontend/src/__tests__/memoryGraph.test.ts](../../frontend/src/__tests__/memoryGraph.test.ts)
- [frontend/src/__tests__/runtimeConfigSources.test.ts](../../frontend/src/__tests__/runtimeConfigSources.test.ts)

#### frontend/src/auth

- [frontend/src/auth/api.ts](../../frontend/src/auth/api.ts)
- [frontend/src/auth/session.ts](../../frontend/src/auth/session.ts)

#### frontend/src/auth/__tests__

- [frontend/src/auth/__tests__/session.test.ts](../../frontend/src/auth/__tests__/session.test.ts)

#### frontend/src/components/account

- [frontend/src/components/account/UserManagementPanel.vue](../../frontend/src/components/account/UserManagementPanel.vue)

#### frontend/src/components/account/__tests__

- [frontend/src/components/account/__tests__/UserManagementPanel.test.ts](../../frontend/src/components/account/__tests__/UserManagementPanel.test.ts)

#### frontend/src/components/chat

- [frontend/src/components/chat/ChatPanel.vue](../../frontend/src/components/chat/ChatPanel.vue)
- [frontend/src/components/chat/InputBar.vue](../../frontend/src/components/chat/InputBar.vue)
- [frontend/src/components/chat/LiveChatPanel.vue](../../frontend/src/components/chat/LiveChatPanel.vue)
- [frontend/src/components/chat/MessageBubble.vue](../../frontend/src/components/chat/MessageBubble.vue)
- [frontend/src/components/chat/MessageList.vue](../../frontend/src/components/chat/MessageList.vue)
- [frontend/src/components/chat/SpeakingIndicator.vue](../../frontend/src/components/chat/SpeakingIndicator.vue)
- [frontend/src/components/chat/TypingIndicator.vue](../../frontend/src/components/chat/TypingIndicator.vue)
- [frontend/src/components/chat/VoiceButton.vue](../../frontend/src/components/chat/VoiceButton.vue)
- [frontend/src/components/chat/WelcomeScreen.vue](../../frontend/src/components/chat/WelcomeScreen.vue)

#### frontend/src/components/chat/__tests__

- [frontend/src/components/chat/__tests__/InputBar.test.ts](../../frontend/src/components/chat/__tests__/InputBar.test.ts)
- [frontend/src/components/chat/__tests__/MessageBubble.test.ts](../../frontend/src/components/chat/__tests__/MessageBubble.test.ts)
- [frontend/src/components/chat/__tests__/MessageList.test.ts](../../frontend/src/components/chat/__tests__/MessageList.test.ts)
- [frontend/src/components/chat/__tests__/TypingIndicator.test.ts](../../frontend/src/components/chat/__tests__/TypingIndicator.test.ts)
- [frontend/src/components/chat/__tests__/WelcomeScreen.test.ts](../../frontend/src/components/chat/__tests__/WelcomeScreen.test.ts)

#### frontend/src/components/dashboard

- [frontend/src/components/dashboard/ConversationSandbox.vue](../../frontend/src/components/dashboard/ConversationSandbox.vue)
- [frontend/src/components/dashboard/LiveOperationsWorkspace.vue](../../frontend/src/components/dashboard/LiveOperationsWorkspace.vue)
- [frontend/src/components/dashboard/PreflightDrawer.vue](../../frontend/src/components/dashboard/PreflightDrawer.vue)
- [frontend/src/components/dashboard/ToolApprovalQueue.vue](../../frontend/src/components/dashboard/ToolApprovalQueue.vue)
- [frontend/src/components/dashboard/ValidationWorkspace.vue](../../frontend/src/components/dashboard/ValidationWorkspace.vue)

#### frontend/src/components/dashboard/__tests__

- [frontend/src/components/dashboard/__tests__/DashboardDomains.test.ts](../../frontend/src/components/dashboard/__tests__/DashboardDomains.test.ts)
- [frontend/src/components/dashboard/__tests__/LiveOperationsWorkspace.test.ts](../../frontend/src/components/dashboard/__tests__/LiveOperationsWorkspace.test.ts)

#### frontend/src/components/layout

- [frontend/src/components/layout/AppLayout.vue](../../frontend/src/components/layout/AppLayout.vue)
- [frontend/src/components/layout/InteractivePanel.vue](../../frontend/src/components/layout/InteractivePanel.vue)
- [frontend/src/components/layout/LeftDrawer.vue](../../frontend/src/components/layout/LeftDrawer.vue)
- [frontend/src/components/layout/MemoryCards.vue](../../frontend/src/components/layout/MemoryCards.vue)
- [frontend/src/components/layout/PersonaCard.vue](../../frontend/src/components/layout/PersonaCard.vue)
- [frontend/src/components/layout/QuickControls.vue](../../frontend/src/components/layout/QuickControls.vue)
- [frontend/src/components/layout/SessionStats.vue](../../frontend/src/components/layout/SessionStats.vue)
- [frontend/src/components/layout/TitleBar.vue](../../frontend/src/components/layout/TitleBar.vue)

#### frontend/src/components/layout/__tests__

- [frontend/src/components/layout/__tests__/AppLayout.test.ts](../../frontend/src/components/layout/__tests__/AppLayout.test.ts)
- [frontend/src/components/layout/__tests__/InteractivePanel.test.ts](../../frontend/src/components/layout/__tests__/InteractivePanel.test.ts)
- [frontend/src/components/layout/__tests__/TitleBar.test.ts](../../frontend/src/components/layout/__tests__/TitleBar.test.ts)

#### frontend/src/components/live2d

- [frontend/src/components/live2d/Live2DRenderer.vue](../../frontend/src/components/live2d/Live2DRenderer.vue)
- [frontend/src/components/live2d/PopOutButton.vue](../../frontend/src/components/live2d/PopOutButton.vue)
- [frontend/src/components/live2d/SubtitleOverlay.vue](../../frontend/src/components/live2d/SubtitleOverlay.vue)
- [frontend/src/components/live2d/useInteraction.ts](../../frontend/src/components/live2d/useInteraction.ts)
- [frontend/src/components/live2d/useLive2D.ts](../../frontend/src/components/live2d/useLive2D.ts)
- [frontend/src/components/live2d/useLive2DModel.ts](../../frontend/src/components/live2d/useLive2DModel.ts)
- [frontend/src/components/live2d/useParameterTimeline.test.ts](../../frontend/src/components/live2d/useParameterTimeline.test.ts)
- [frontend/src/components/live2d/useParameterTimeline.ts](../../frontend/src/components/live2d/useParameterTimeline.ts)
- [frontend/src/components/live2d/usePixiApp.ts](../../frontend/src/components/live2d/usePixiApp.ts)

#### frontend/src/components/live2d/__tests__

- [frontend/src/components/live2d/__tests__/Live2DRenderer.test.ts](../../frontend/src/components/live2d/__tests__/Live2DRenderer.test.ts)

#### frontend/src/components/meme

- [frontend/src/components/meme/MemeWorkspace.vue](../../frontend/src/components/meme/MemeWorkspace.vue)

#### frontend/src/components/memory

- [frontend/src/components/memory/MemoryGraph.vue](../../frontend/src/components/memory/MemoryGraph.vue)
- [frontend/src/components/memory/MemoryGraphControls.vue](../../frontend/src/components/memory/MemoryGraphControls.vue)
- [frontend/src/components/memory/MemoryGraphEdge.vue](../../frontend/src/components/memory/MemoryGraphEdge.vue)
- [frontend/src/components/memory/MemoryGraphNode.vue](../../frontend/src/components/memory/MemoryGraphNode.vue)
- [frontend/src/components/memory/MemoryPanel.vue](../../frontend/src/components/memory/MemoryPanel.vue)
- [frontend/src/components/memory/MemoryWorkspace.vue](../../frontend/src/components/memory/MemoryWorkspace.vue)

#### frontend/src/components/minecraft

- [frontend/src/components/minecraft/BotDashboard.vue](../../frontend/src/components/minecraft/BotDashboard.vue)

#### frontend/src/components/personality

- [frontend/src/components/personality/PersonalityPanel.vue](../../frontend/src/components/personality/PersonalityPanel.vue)

#### frontend/src/components/program

- [frontend/src/components/program/ProgramReplayPanel.vue](../../frontend/src/components/program/ProgramReplayPanel.vue)
- [frontend/src/components/program/ProgramRunPanel.vue](../../frontend/src/components/program/ProgramRunPanel.vue)
- [frontend/src/components/program/ProgramScriptEditor.vue](../../frontend/src/components/program/ProgramScriptEditor.vue)
- [frontend/src/components/program/ProgramWorkspace.vue](../../frontend/src/components/program/ProgramWorkspace.vue)

#### frontend/src/components/program/__tests__

- [frontend/src/components/program/__tests__/ProgramControls.test.ts](../../frontend/src/components/program/__tests__/ProgramControls.test.ts)

#### frontend/src/components/settings

- [frontend/src/components/settings/BackgroundSettings.vue](../../frontend/src/components/settings/BackgroundSettings.vue)
- [frontend/src/components/settings/SettingsPanel.vue](../../frontend/src/components/settings/SettingsPanel.vue)

#### frontend/src/components/settings/__tests__

- [frontend/src/components/settings/__tests__/SettingsPanel.test.ts](../../frontend/src/components/settings/__tests__/SettingsPanel.test.ts)

#### frontend/src/components/shared

- [frontend/src/components/shared/BentoCard.vue](../../frontend/src/components/shared/BentoCard.vue)
- [frontend/src/components/shared/BentoGrid.vue](../../frontend/src/components/shared/BentoGrid.vue)
- [frontend/src/components/shared/SceneEffects.vue](../../frontend/src/components/shared/SceneEffects.vue)
- [frontend/src/components/shared/SectionTabs.vue](../../frontend/src/components/shared/SectionTabs.vue)

#### frontend/src/components/shared/__tests__

- [frontend/src/components/shared/__tests__/BentoGrid.test.ts](../../frontend/src/components/shared/__tests__/BentoGrid.test.ts)
- [frontend/src/components/shared/__tests__/SectionTabs.test.ts](../../frontend/src/components/shared/__tests__/SectionTabs.test.ts)

#### frontend/src/components/singing

- [frontend/src/components/singing/MusicCard.test.ts](../../frontend/src/components/singing/MusicCard.test.ts)
- [frontend/src/components/singing/MusicCard.vue](../../frontend/src/components/singing/MusicCard.vue)
- [frontend/src/components/singing/PlaybackControls.test.ts](../../frontend/src/components/singing/PlaybackControls.test.ts)
- [frontend/src/components/singing/PlaybackControls.vue](../../frontend/src/components/singing/PlaybackControls.vue)
- [frontend/src/components/singing/ProcessTimeline.vue](../../frontend/src/components/singing/ProcessTimeline.vue)
- [frontend/src/components/singing/WaveformDisplay.vue](../../frontend/src/components/singing/WaveformDisplay.vue)

#### frontend/src/composables

- [frontend/src/composables/chatTaskGate.ts](../../frontend/src/composables/chatTaskGate.ts)
- [frontend/src/composables/chatTransport.ts](../../frontend/src/composables/chatTransport.ts)
- [frontend/src/composables/commandTasks.ts](../../frontend/src/composables/commandTasks.ts)
- [frontend/src/composables/useChat.ts](../../frontend/src/composables/useChat.ts)
- [frontend/src/composables/useDanmaku.ts](../../frontend/src/composables/useDanmaku.ts)
- [frontend/src/composables/useGsap.ts](../../frontend/src/composables/useGsap.ts)
- [frontend/src/composables/useHoverPhysics.ts](../../frontend/src/composables/useHoverPhysics.ts)
- [frontend/src/composables/useMessageStore.ts](../../frontend/src/composables/useMessageStore.ts)
- [frontend/src/composables/useMobile.ts](../../frontend/src/composables/useMobile.ts)
- [frontend/src/composables/useScrollTrigger.ts](../../frontend/src/composables/useScrollTrigger.ts)
- [frontend/src/composables/useSinging.ts](../../frontend/src/composables/useSinging.ts)
- [frontend/src/composables/useSocket.ts](../../frontend/src/composables/useSocket.ts)
- [frontend/src/composables/useSubtitle.ts](../../frontend/src/composables/useSubtitle.ts)
- [frontend/src/composables/useVoice.ts](../../frontend/src/composables/useVoice.ts)

#### frontend/src/composables/__tests__

- [frontend/src/composables/__tests__/chatTaskGate.test.ts](../../frontend/src/composables/__tests__/chatTaskGate.test.ts)
- [frontend/src/composables/__tests__/chatTransport.test.ts](../../frontend/src/composables/__tests__/chatTransport.test.ts)
- [frontend/src/composables/__tests__/useChat.test.ts](../../frontend/src/composables/__tests__/useChat.test.ts)
- [frontend/src/composables/__tests__/useDanmaku.test.ts](../../frontend/src/composables/__tests__/useDanmaku.test.ts)
- [frontend/src/composables/__tests__/useGsap.test.ts](../../frontend/src/composables/__tests__/useGsap.test.ts)
- [frontend/src/composables/__tests__/useHoverPhysics.test.ts](../../frontend/src/composables/__tests__/useHoverPhysics.test.ts)
- [frontend/src/composables/__tests__/useLive2D.test.ts](../../frontend/src/composables/__tests__/useLive2D.test.ts)
- [frontend/src/composables/__tests__/useScrollTrigger.test.ts](../../frontend/src/composables/__tests__/useScrollTrigger.test.ts)
- [frontend/src/composables/__tests__/useSocket.same-origin.test.ts](../../frontend/src/composables/__tests__/useSocket.same-origin.test.ts)
- [frontend/src/composables/__tests__/useSubtitle.test.ts](../../frontend/src/composables/__tests__/useSubtitle.test.ts)

#### frontend/src/constants

- [frontend/src/constants/socket-events.ts](../../frontend/src/constants/socket-events.ts)

#### frontend/src/earth-prototype

- [frontend/src/earth-prototype/EarthPrototype.vue](../../frontend/src/earth-prototype/EarthPrototype.vue)
- [frontend/src/earth-prototype/main.ts](../../frontend/src/earth-prototype/main.ts)

#### frontend/src/features/earth

- [frontend/src/features/earth/contracts.ts](../../frontend/src/features/earth/contracts.ts)
- [frontend/src/features/earth/controller.test.ts](../../frontend/src/features/earth/controller.test.ts)
- [frontend/src/features/earth/controller.ts](../../frontend/src/features/earth/controller.ts)
- [frontend/src/features/earth/EarthWorkspace.test.ts](../../frontend/src/features/earth/EarthWorkspace.test.ts)
- [frontend/src/features/earth/EarthWorkspace.vue](../../frontend/src/features/earth/EarthWorkspace.vue)
- [frontend/src/features/earth/index.ts](../../frontend/src/features/earth/index.ts)
- [frontend/src/features/earth/mount.ts](../../frontend/src/features/earth/mount.ts)

#### frontend/src/features/earth/adapters

- [frontend/src/features/earth/adapters/cesium.test.ts](../../frontend/src/features/earth/adapters/cesium.test.ts)
- [frontend/src/features/earth/adapters/cesium.ts](../../frontend/src/features/earth/adapters/cesium.ts)
- [frontend/src/features/earth/adapters/microphone.test.ts](../../frontend/src/features/earth/adapters/microphone.test.ts)
- [frontend/src/features/earth/adapters/microphone.ts](../../frontend/src/features/earth/adapters/microphone.ts)
- [frontend/src/features/earth/adapters/narration.ts](../../frontend/src/features/earth/adapters/narration.ts)
- [frontend/src/features/earth/adapters/socket.ts](../../frontend/src/features/earth/adapters/socket.ts)

#### frontend/src/live

- [frontend/src/live/audio.test.ts](../../frontend/src/live/audio.test.ts)
- [frontend/src/live/audio.ts](../../frontend/src/live/audio.ts)
- [frontend/src/live/bgm.test.ts](../../frontend/src/live/bgm.test.ts)
- [frontend/src/live/bgm.ts](../../frontend/src/live/bgm.ts)
- [frontend/src/live/bootstrap.ts](../../frontend/src/live/bootstrap.ts)
- [frontend/src/live/controller.ts](../../frontend/src/live/controller.ts)
- [frontend/src/live/main.ts](../../frontend/src/live/main.ts)
- [frontend/src/live/public-live-socket.ts](../../frontend/src/live/public-live-socket.ts)
- [frontend/src/live/review-socket.ts](../../frontend/src/live/review-socket.ts)
- [frontend/src/live/socket-runtime.ts](../../frontend/src/live/socket-runtime.ts)
- [frontend/src/live/styles.css](../../frontend/src/live/styles.css)
- [frontend/src/live/view.ts](../../frontend/src/live/view.ts)

#### frontend/src/live/__tests__

- [frontend/src/live/__tests__/bootstrap.test.ts](../../frontend/src/live/__tests__/bootstrap.test.ts)
- [frontend/src/live/__tests__/controller.test.ts](../../frontend/src/live/__tests__/controller.test.ts)
- [frontend/src/live/__tests__/entry-styles.test.ts](../../frontend/src/live/__tests__/entry-styles.test.ts)
- [frontend/src/live/__tests__/public-live-socket.test.ts](../../frontend/src/live/__tests__/public-live-socket.test.ts)
- [frontend/src/live/__tests__/review-socket.test.ts](../../frontend/src/live/__tests__/review-socket.test.ts)
- [frontend/src/live/__tests__/socket-runtime.test.ts](../../frontend/src/live/__tests__/socket-runtime.test.ts)
- [frontend/src/live/__tests__/styles.test.ts](../../frontend/src/live/__tests__/styles.test.ts)
- [frontend/src/live/__tests__/view.test.ts](../../frontend/src/live/__tests__/view.test.ts)

#### frontend/src/live/review

- [frontend/src/live/review/catalog.ts](../../frontend/src/live/review/catalog.ts)
- [frontend/src/live/review/plugin.ts](../../frontend/src/live/review/plugin.ts)
- [frontend/src/live/review/request.ts](../../frontend/src/live/review/request.ts)
- [frontend/src/live/review/runtime.ts](../../frontend/src/live/review/runtime.ts)

#### frontend/src/minecraft-gameplay

- [frontend/src/minecraft-gameplay/catalog.ts](../../frontend/src/minecraft-gameplay/catalog.ts)
- [frontend/src/minecraft-gameplay/layout.test.ts](../../frontend/src/minecraft-gameplay/layout.test.ts)
- [frontend/src/minecraft-gameplay/layout.ts](../../frontend/src/minecraft-gameplay/layout.ts)
- [frontend/src/minecraft-gameplay/main.ts](../../frontend/src/minecraft-gameplay/main.ts)
- [frontend/src/minecraft-gameplay/page.test.ts](../../frontend/src/minecraft-gameplay/page.test.ts)
- [frontend/src/minecraft-gameplay/page.ts](../../frontend/src/minecraft-gameplay/page.ts)
- [frontend/src/minecraft-gameplay/styles.css](../../frontend/src/minecraft-gameplay/styles.css)

#### frontend/src/review

- [frontend/src/review/contracts.ts](../../frontend/src/review/contracts.ts)
- [frontend/src/review/disposable.ts](../../frontend/src/review/disposable.ts)
- [frontend/src/review/layout.ts](../../frontend/src/review/layout.ts)
- [frontend/src/review/live2d-stage.test.ts](../../frontend/src/review/live2d-stage.test.ts)
- [frontend/src/review/live2d-stage.ts](../../frontend/src/review/live2d-stage.ts)
- [frontend/src/review/registry.ts](../../frontend/src/review/registry.ts)
- [frontend/src/review/review-lip-sync.test.ts](../../frontend/src/review/review-lip-sync.test.ts)
- [frontend/src/review/review-lip-sync.ts](../../frontend/src/review/review-lip-sync.ts)
- [frontend/src/review/timeline.ts](../../frontend/src/review/timeline.ts)

#### frontend/src/review/__tests__

- [frontend/src/review/__tests__/layout.test.ts](../../frontend/src/review/__tests__/layout.test.ts)

#### frontend/src/review/live2d-performance

- [frontend/src/review/live2d-performance/catalog.ts](../../frontend/src/review/live2d-performance/catalog.ts)
- [frontend/src/review/live2d-performance/main.test.ts](../../frontend/src/review/live2d-performance/main.test.ts)
- [frontend/src/review/live2d-performance/main.ts](../../frontend/src/review/live2d-performance/main.ts)
- [frontend/src/review/live2d-performance/performanceRuntime.test.ts](../../frontend/src/review/live2d-performance/performanceRuntime.test.ts)
- [frontend/src/review/live2d-performance/performanceSamples.ts](../../frontend/src/review/live2d-performance/performanceSamples.ts)
- [frontend/src/review/live2d-performance/performanceSequence.ts](../../frontend/src/review/live2d-performance/performanceSequence.ts)
- [frontend/src/review/live2d-performance/styles.css](../../frontend/src/review/live2d-performance/styles.css)

#### frontend/src/router

- [frontend/src/router/index.ts](../../frontend/src/router/index.ts)

#### frontend/src/router/__tests__

- [frontend/src/router/__tests__/router.test.ts](../../frontend/src/router/__tests__/router.test.ts)

#### frontend/src/services

- [frontend/src/services/commandTasks.test.ts](../../frontend/src/services/commandTasks.test.ts)
- [frontend/src/services/commandTasks.ts](../../frontend/src/services/commandTasks.ts)
- [frontend/src/services/messageRepository.ts](../../frontend/src/services/messageRepository.ts)
- [frontend/src/services/programScripts.ts](../../frontend/src/services/programScripts.ts)
- [frontend/src/services/runtimeStatus.ts](../../frontend/src/services/runtimeStatus.ts)
- [frontend/src/services/socket.ts](../../frontend/src/services/socket.ts)

#### frontend/src/services/__tests__

- [frontend/src/services/__tests__/runtimeStatus.test.ts](../../frontend/src/services/__tests__/runtimeStatus.test.ts)

#### frontend/src/shared/audio

- [frontend/src/shared/audio/lipSync.ts](../../frontend/src/shared/audio/lipSync.ts)
- [frontend/src/shared/audio/mouthEnvelope.ts](../../frontend/src/shared/audio/mouthEnvelope.ts)
- [frontend/src/shared/audio/pcmStreamPlayback.test.ts](../../frontend/src/shared/audio/pcmStreamPlayback.test.ts)
- [frontend/src/shared/audio/pcmStreamPlayback.ts](../../frontend/src/shared/audio/pcmStreamPlayback.ts)
- [frontend/src/shared/audio/playback.test.ts](../../frontend/src/shared/audio/playback.test.ts)
- [frontend/src/shared/audio/playback.ts](../../frontend/src/shared/audio/playback.ts)

#### frontend/src/shared/broadcast

- [frontend/src/shared/broadcast/mediaOwnership.ts](../../frontend/src/shared/broadcast/mediaOwnership.ts)
- [frontend/src/shared/broadcast/public-activity.css](../../frontend/src/shared/broadcast/public-activity.css)
- [frontend/src/shared/broadcast/publicActivity.test.ts](../../frontend/src/shared/broadcast/publicActivity.test.ts)
- [frontend/src/shared/broadcast/publicActivity.ts](../../frontend/src/shared/broadcast/publicActivity.ts)
- [frontend/src/shared/broadcast/publicActivityView.ts](../../frontend/src/shared/broadcast/publicActivityView.ts)

#### frontend/src/shared/contracts

- [frontend/src/shared/contracts/socket-events.ts](../../frontend/src/shared/contracts/socket-events.ts)

#### frontend/src/shared/live2d

- [frontend/src/shared/live2d/Companion.vue](../../frontend/src/shared/live2d/Companion.vue)
- [frontend/src/shared/live2d/maoPerformanceProfile.ts](../../frontend/src/shared/live2d/maoPerformanceProfile.ts)
- [frontend/src/shared/live2d/mouthParameter.ts](../../frontend/src/shared/live2d/mouthParameter.ts)
- [frontend/src/shared/live2d/performanceContract.test.ts](../../frontend/src/shared/live2d/performanceContract.test.ts)
- [frontend/src/shared/live2d/performanceContract.ts](../../frontend/src/shared/live2d/performanceContract.ts)
- [frontend/src/shared/live2d/performanceController.test.ts](../../frontend/src/shared/live2d/performanceController.test.ts)
- [frontend/src/shared/live2d/performanceController.ts](../../frontend/src/shared/live2d/performanceController.ts)
- [frontend/src/shared/live2d/performanceObservability.ts](../../frontend/src/shared/live2d/performanceObservability.ts)
- [frontend/src/shared/live2d/performanceProfile.test.ts](../../frontend/src/shared/live2d/performanceProfile.test.ts)
- [frontend/src/shared/live2d/performanceProfile.ts](../../frontend/src/shared/live2d/performanceProfile.ts)
- [frontend/src/shared/live2d/renderer.test.ts](../../frontend/src/shared/live2d/renderer.test.ts)
- [frontend/src/shared/live2d/renderer.ts](../../frontend/src/shared/live2d/renderer.ts)

#### frontend/src/shared/transport

- [frontend/src/shared/transport/liveSocket.ts](../../frontend/src/shared/transport/liveSocket.ts)
- [frontend/src/shared/transport/publicLiveSocket.ts](../../frontend/src/shared/transport/publicLiveSocket.ts)

#### frontend/src/singing

- [frontend/src/singing/playback-sync.test.ts](../../frontend/src/singing/playback-sync.test.ts)
- [frontend/src/singing/playback-sync.ts](../../frontend/src/singing/playback-sync.ts)

#### frontend/src/stores

- [frontend/src/stores/chat.ts](../../frontend/src/stores/chat.ts)
- [frontend/src/stores/connection.ts](../../frontend/src/stores/connection.ts)
- [frontend/src/stores/danmaku.ts](../../frontend/src/stores/danmaku.ts)
- [frontend/src/stores/dashboardStore.ts](../../frontend/src/stores/dashboardStore.ts)
- [frontend/src/stores/memory.ts](../../frontend/src/stores/memory.ts)
- [frontend/src/stores/minecraft.ts](../../frontend/src/stores/minecraft.ts)
- [frontend/src/stores/modelLoading.ts](../../frontend/src/stores/modelLoading.ts)
- [frontend/src/stores/personality.ts](../../frontend/src/stores/personality.ts)
- [frontend/src/stores/singing.ts](../../frontend/src/stores/singing.ts)
- [frontend/src/stores/subtitle.ts](../../frontend/src/stores/subtitle.ts)

#### frontend/src/stores/__tests__

- [frontend/src/stores/__tests__/chat.test.ts](../../frontend/src/stores/__tests__/chat.test.ts)
- [frontend/src/stores/__tests__/connection.test.ts](../../frontend/src/stores/__tests__/connection.test.ts)
- [frontend/src/stores/__tests__/danmaku.test.ts](../../frontend/src/stores/__tests__/danmaku.test.ts)
- [frontend/src/stores/__tests__/memory.test.ts](../../frontend/src/stores/__tests__/memory.test.ts)
- [frontend/src/stores/__tests__/minecraft.test.ts](../../frontend/src/stores/__tests__/minecraft.test.ts)
- [frontend/src/stores/__tests__/modelLoading.test.ts](../../frontend/src/stores/__tests__/modelLoading.test.ts)
- [frontend/src/stores/__tests__/personality.test.ts](../../frontend/src/stores/__tests__/personality.test.ts)
- [frontend/src/stores/__tests__/subtitle.test.ts](../../frontend/src/stores/__tests__/subtitle.test.ts)

#### frontend/src/styles

- [frontend/src/styles/animations.css](../../frontend/src/styles/animations.css)
- [frontend/src/styles/graph.css](../../frontend/src/styles/graph.css)
- [frontend/src/styles/mobile.css](../../frontend/src/styles/mobile.css)
- [frontend/src/styles/themes.css](../../frontend/src/styles/themes.css)

#### frontend/src/tts-failover

- [frontend/src/tts-failover/catalog.ts](../../frontend/src/tts-failover/catalog.ts)
- [frontend/src/tts-failover/main.test.ts](../../frontend/src/tts-failover/main.test.ts)
- [frontend/src/tts-failover/main.ts](../../frontend/src/tts-failover/main.ts)
- [frontend/src/tts-failover/styles.css](../../frontend/src/tts-failover/styles.css)

#### frontend/src/types

- [frontend/src/types/chat.ts](../../frontend/src/types/chat.ts)
- [frontend/src/types/electron.d.ts](../../frontend/src/types/electron.d.ts)
- [frontend/src/types/live2d.ts](../../frontend/src/types/live2d.ts)
- [frontend/src/types/memoryGraph.ts](../../frontend/src/types/memoryGraph.ts)
- [frontend/src/types/minecraft-stage.ts](../../frontend/src/types/minecraft-stage.ts)
- [frontend/src/types/model-loading.ts](../../frontend/src/types/model-loading.ts)
- [frontend/src/types/runtime-status.ts](../../frontend/src/types/runtime-status.ts)
- [frontend/src/types/singing.ts](../../frontend/src/types/singing.ts)
- [frontend/src/types/socket-events.ts](../../frontend/src/types/socket-events.ts)

#### frontend/src/views

- [frontend/src/views/AccountPage.vue](../../frontend/src/views/AccountPage.vue)
- [frontend/src/views/DashboardPage.vue](../../frontend/src/views/DashboardPage.vue)

#### frontend/src/views/__tests__

- [frontend/src/views/__tests__/AccountPage.test.ts](../../frontend/src/views/__tests__/AccountPage.test.ts)
- [frontend/src/views/__tests__/DashboardPage.test.ts](../../frontend/src/views/__tests__/DashboardPage.test.ts)

#### frontend/tests

- [frontend/tests/live-review-entry.test.ts](../../frontend/tests/live-review-entry.test.ts)
- [frontend/tests/live-review-plugin.test.ts](../../frontend/tests/live-review-plugin.test.ts)
- [frontend/tests/live2d-idle-motion.test.ts](../../frontend/tests/live2d-idle-motion.test.ts)
- [frontend/tests/live2d-performance-review-plugin.test.ts](../../frontend/tests/live2d-performance-review-plugin.test.ts)
- [frontend/tests/minecraft-gameplay-review-plugin.test.ts](../../frontend/tests/minecraft-gameplay-review-plugin.test.ts)
- [frontend/tests/minecraft-obs-adapter.test.ts](../../frontend/tests/minecraft-obs-adapter.test.ts)
- [frontend/tests/minecraft-review-client.test.ts](../../frontend/tests/minecraft-review-client.test.ts)
- [frontend/tests/review-adapters.test.ts](../../frontend/tests/review-adapters.test.ts)
- [frontend/tests/review-assertions.test.ts](../../frontend/tests/review-assertions.test.ts)
- [frontend/tests/review-browser.test.ts](../../frontend/tests/review-browser.test.ts)
- [frontend/tests/review-core.test.ts](../../frontend/tests/review-core.test.ts)
- [frontend/tests/review-options.test.ts](../../frontend/tests/review-options.test.ts)
- [frontend/tests/review-orchestrator.test.ts](../../frontend/tests/review-orchestrator.test.ts)
- [frontend/tests/review-plugin-lifecycle.test.ts](../../frontend/tests/review-plugin-lifecycle.test.ts)
- [frontend/tests/review-prune.test.ts](../../frontend/tests/review-prune.test.ts)
- [frontend/tests/sites-package.test.mjs](../../frontend/tests/sites-package.test.mjs)
- [frontend/tests/sites-worker.test.mjs](../../frontend/tests/sites-worker.test.mjs)
- [frontend/tests/tts-failover-review-plugin.test.ts](../../frontend/tests/tts-failover-review-plugin.test.ts)
- [frontend/tests/tts-harness-contract.test.ts](../../frontend/tests/tts-harness-contract.test.ts)
- [frontend/tests/tts-review-client.test.ts](../../frontend/tests/tts-review-client.test.ts)

#### frontend/worker

- [frontend/worker/sites-static.mjs](../../frontend/worker/sites-static.mjs)

### observability

#### observability

- [observability/alertmanager.yml](../../observability/alertmanager.yml)
- [observability/docker-compose.yml](../../observability/docker-compose.yml)
- [observability/Dockerfile.notifier](../../observability/Dockerfile.notifier)
- [observability/loki-config.yaml](../../observability/loki-config.yaml)
- [observability/otel-collector-config.yaml](../../observability/otel-collector-config.yaml)
- [observability/prometheus.yml](../../observability/prometheus.yml)
- [observability/tempo-config.yaml](../../observability/tempo-config.yaml)

#### observability/alerts

- [observability/alerts/rules.yml](../../observability/alerts/rules.yml)

#### observability/grafana/dashboards

- [observability/grafana/dashboards/01-overview.json](../../observability/grafana/dashboards/01-overview.json)
- [observability/grafana/dashboards/02-langgraph-pipeline.json](../../observability/grafana/dashboards/02-langgraph-pipeline.json)
- [observability/grafana/dashboards/03-rag-performance.json](../../observability/grafana/dashboards/03-rag-performance.json)
- [observability/grafana/dashboards/04-cost-and-tokens.json](../../observability/grafana/dashboards/04-cost-and-tokens.json)

#### observability/grafana/provisioning/dashboards

- [observability/grafana/provisioning/dashboards/dashboards.yml](../../observability/grafana/provisioning/dashboards/dashboards.yml)

#### observability/grafana/provisioning/datasources

- [observability/grafana/provisioning/datasources/datasources.yml](../../observability/grafana/provisioning/datasources/datasources.yml)

### openspec

#### openspec/changes/add-mcbot-readable-agency

- [openspec/changes/add-mcbot-readable-agency/.openspec.yaml](../../openspec/changes/add-mcbot-readable-agency/.openspec.yaml)
- [openspec/changes/add-mcbot-readable-agency/design.md](../../openspec/changes/add-mcbot-readable-agency/design.md)
- [openspec/changes/add-mcbot-readable-agency/proposal.md](../../openspec/changes/add-mcbot-readable-agency/proposal.md)
- [openspec/changes/add-mcbot-readable-agency/tasks.md](../../openspec/changes/add-mcbot-readable-agency/tasks.md)

#### openspec/changes/add-mcbot-readable-agency/specs/livestream-narration-director

- [openspec/changes/add-mcbot-readable-agency/specs/livestream-narration-director/spec.md](../../openspec/changes/add-mcbot-readable-agency/specs/livestream-narration-director/spec.md)

#### openspec/changes/add-mcbot-readable-agency/specs/minecraft-broadcast-presentation

- [openspec/changes/add-mcbot-readable-agency/specs/minecraft-broadcast-presentation/spec.md](../../openspec/changes/add-mcbot-readable-agency/specs/minecraft-broadcast-presentation/spec.md)

#### openspec/changes/add-mcbot-readable-agency/specs/minecraft-public-activity

- [openspec/changes/add-mcbot-readable-agency/specs/minecraft-public-activity/spec.md](../../openspec/changes/add-mcbot-readable-agency/specs/minecraft-public-activity/spec.md)

### pitch

#### pitch

- [pitch/.gitignore](../../pitch/.gitignore)
- [pitch/Animetta-投资人汇报-华为胶片版.pptx](../../pitch/Animetta-%E6%8A%95%E8%B5%84%E4%BA%BA%E6%B1%87%E6%8A%A5-%E5%8D%8E%E4%B8%BA%E8%83%B6%E7%89%87%E7%89%88.pptx)
- [pitch/Animetta-投资人简报.pptx](../../pitch/Animetta-%E6%8A%95%E8%B5%84%E4%BA%BA%E7%AE%80%E6%8A%A5.pptx)
- [pitch/build_deck_hw.js](../../pitch/build_deck_hw.js)
- [pitch/build_deck.js](../../pitch/build_deck.js)
- [pitch/package-lock.json](../../pitch/package-lock.json)
- [pitch/package.json](../../pitch/package.json)
- [pitch/qa_check.py](../../pitch/qa_check.py)

### scripts

#### scripts

- [scripts/baseline_golden_path.py](../../scripts/baseline_golden_path.py)
- [scripts/bench.py](../../scripts/bench.py)
- [scripts/benchmark_host_tts.py](../../scripts/benchmark_host_tts.py)
- [scripts/benchmark_startup.py](../../scripts/benchmark_startup.py)
- [scripts/benchmark_storage.py](../../scripts/benchmark_storage.py)
- [scripts/check_architecture_boundaries.py](../../scripts/check_architecture_boundaries.py)
- [scripts/check_minecraft_architecture.py](../../scripts/check_minecraft_architecture.py)
- [scripts/check_python_lock.py](../../scripts/check_python_lock.py)
- [scripts/check_secrets.py](../../scripts/check_secrets.py)
- [scripts/check_source_standards.py](../../scripts/check_source_standards.py)
- [scripts/collect_danmaku.py](../../scripts/collect_danmaku.py)
- [scripts/collect_live_danmaku.py](../../scripts/collect_live_danmaku.py)
- [scripts/conversation_continuity_canary.py](../../scripts/conversation_continuity_canary.py)
- [scripts/demucs_fix.py](../../scripts/demucs_fix.py)
- [scripts/download-models.sh](../../scripts/download-models.sh)
- [scripts/generate_gamebot_v2_contracts.py](../../scripts/generate_gamebot_v2_contracts.py)
- [scripts/generate_minecraft_mission_contracts.py](../../scripts/generate_minecraft_mission_contracts.py)
- [scripts/health_check.py](../../scripts/health_check.py)
- [scripts/manage_users.py](../../scripts/manage_users.py)
- [scripts/measure_storage_telemetry.ps1](../../scripts/measure_storage_telemetry.ps1)
- [scripts/minecraft_adaptive_micro_gate.py](../../scripts/minecraft_adaptive_micro_gate.py)
- [scripts/minecraft_adaptive_showcase.py](../../scripts/minecraft_adaptive_showcase.py)
- [scripts/minecraft_gameplay_review_harness.py](../../scripts/minecraft_gameplay_review_harness.py)
- [scripts/minecraft_real_model_contract.py](../../scripts/minecraft_real_model_contract.py)
- [scripts/probe_release_turn.py](../../scripts/probe_release_turn.py)
- [scripts/qwen_preflight.py](../../scripts/qwen_preflight.py)
- [scripts/README.md](../../scripts/README.md)
- [scripts/release_runtime_gate.py](../../scripts/release_runtime_gate.py)
- [scripts/reset_observability.py](../../scripts/reset_observability.py)
- [scripts/route_smoke.py](../../scripts/route_smoke.py)
- [scripts/runtime_lifecycle.py](../../scripts/runtime_lifecycle.py)
- [scripts/rvc_preflight.py](../../scripts/rvc_preflight.py)
- [scripts/smoke_bilibili_room.py](../../scripts/smoke_bilibili_room.py)
- [scripts/smoke_real_profile.py](../../scripts/smoke_real_profile.py)
- [scripts/soak_golden_path.py](../../scripts/soak_golden_path.py)
- [scripts/sync_feishu_to_docs.py](../../scripts/sync_feishu_to_docs.py)
- [scripts/tts_audition.py](../../scripts/tts_audition.py)
- [scripts/tts_failover_review_harness.py](../../scripts/tts_failover_review_harness.py)
- [scripts/validate-events.py](../../scripts/validate-events.py)
- [scripts/verify_minecraft_migration.py](../../scripts/verify_minecraft_migration.py)
- [scripts/voyager_real_e2e.py](../../scripts/voyager_real_e2e.py)

#### scripts/train

- [scripts/train/__init__.py](../../scripts/train/__init__.py)
- [scripts/train/build_index.py](../../scripts/train/build_index.py)
- [scripts/train/cli.py](../../scripts/train/cli.py)
- [scripts/train/deploy.py](../../scripts/train/deploy.py)
- [scripts/train/materialize_dataset.py](../../scripts/train/materialize_dataset.py)
- [scripts/train/prepare_data.py](../../scripts/train/prepare_data.py)
- [scripts/train/prepare_rvc_experiment.py](../../scripts/train/prepare_rvc_experiment.py)
- [scripts/train/README.md](../../scripts/train/README.md)
- [scripts/train/review_data.py](../../scripts/train/review_data.py) — 未提交
- [scripts/train/review_ui.html](../../scripts/train/review_ui.html) — 未提交
- [scripts/train/workspace.py](../../scripts/train/workspace.py)

### services

#### services/mc-mcp

- [services/mc-mcp/.gitignore](../../services/mc-mcp/.gitignore)
- [services/mc-mcp/AGENTS.md](../../services/mc-mcp/AGENTS.md)
- [services/mc-mcp/package-lock.json](../../services/mc-mcp/package-lock.json)
- [services/mc-mcp/package.json](../../services/mc-mcp/package.json)
- [services/mc-mcp/README.md](../../services/mc-mcp/README.md)

#### services/mc-mcp/config

- [services/mc-mcp/config/mc-mcp.json](../../services/mc-mcp/config/mc-mcp.json)

#### services/mc-mcp/server

- [services/mc-mcp/server/docker-compose.yml](../../services/mc-mcp/server/docker-compose.yml)
- [services/mc-mcp/server/ops.json](../../services/mc-mcp/server/ops.json)

#### services/mc-mcp/src

- [services/mc-mcp/src/actionDeadline.js](../../services/mc-mcp/src/actionDeadline.js)
- [services/mc-mcp/src/advancementAdapterV2.js](../../services/mc-mcp/src/advancementAdapterV2.js)
- [services/mc-mcp/src/branch_mine.js](../../services/mc-mcp/src/branch_mine.js)
- [services/mc-mcp/src/clientViewer.js](../../services/mc-mcp/src/clientViewer.js)
- [services/mc-mcp/src/collection.js](../../services/mc-mcp/src/collection.js)
- [services/mc-mcp/src/craftingTable.js](../../services/mc-mcp/src/craftingTable.js)
- [services/mc-mcp/src/equip.js](../../services/mc-mcp/src/equip.js)
- [services/mc-mcp/src/gamebotEvidenceV2.js](../../services/mc-mcp/src/gamebotEvidenceV2.js)
- [services/mc-mcp/src/gamebotRuntimeV2.js](../../services/mc-mcp/src/gamebotRuntimeV2.js)
- [services/mc-mcp/src/index.js](../../services/mc-mcp/src/index.js)
- [services/mc-mcp/src/mine_shaft.js](../../services/mc-mcp/src/mine_shaft.js)
- [services/mc-mcp/src/placement.js](../../services/mc-mcp/src/placement.js)
- [services/mc-mcp/src/safeChat.js](../../services/mc-mcp/src/safeChat.js)
- [services/mc-mcp/src/smelt.js](../../services/mc-mcp/src/smelt.js)

#### services/mc-mcp/src/crafting

- [services/mc-mcp/src/crafting/counts.js](../../services/mc-mcp/src/crafting/counts.js)
- [services/mc-mcp/src/crafting/placement.js](../../services/mc-mcp/src/crafting/placement.js)

#### services/mc-mcp/src/mcp

- [services/mc-mcp/src/mcp/cli.js](../../services/mc-mcp/src/mcp/cli.js)
- [services/mc-mcp/src/mcp/client.js](../../services/mc-mcp/src/mcp/client.js)
- [services/mc-mcp/src/mcp/eventBuffer.js](../../services/mc-mcp/src/mcp/eventBuffer.js)
- [services/mc-mcp/src/mcp/lifecycle.js](../../services/mc-mcp/src/mcp/lifecycle.js)
- [services/mc-mcp/src/mcp/managedServer.js](../../services/mc-mcp/src/mcp/managedServer.js)
- [services/mc-mcp/src/mcp/profile.js](../../services/mc-mcp/src/mcp/profile.js)
- [services/mc-mcp/src/mcp/runtimeClient.js](../../services/mc-mcp/src/mcp/runtimeClient.js)
- [services/mc-mcp/src/mcp/secureState.js](../../services/mc-mcp/src/mcp/secureState.js)
- [services/mc-mcp/src/mcp/server.js](../../services/mc-mcp/src/mcp/server.js)
- [services/mc-mcp/src/mcp/tools.js](../../services/mc-mcp/src/mcp/tools.js)

#### services/mc-mcp/src/resources

- [services/mc-mcp/src/resources/locator.js](../../services/mc-mcp/src/resources/locator.js)
- [services/mc-mcp/src/resources/memory.js](../../services/mc-mcp/src/resources/memory.js)
- [services/mc-mcp/src/resources/memory.test.js](../../services/mc-mcp/src/resources/memory.test.js)
- [services/mc-mcp/src/resources/registry.js](../../services/mc-mcp/src/resources/registry.js)
- [services/mc-mcp/src/resources/registry.test.js](../../services/mc-mcp/src/resources/registry.test.js)
- [services/mc-mcp/src/resources/strategies.js](../../services/mc-mcp/src/resources/strategies.js)

#### services/mc-mcp/src/runtime

- [services/mc-mcp/src/runtime/broadcastMotionPolicy.js](../../services/mc-mcp/src/runtime/broadcastMotionPolicy.js)
- [services/mc-mcp/src/runtime/gamebotV2Adapter.js](../../services/mc-mcp/src/runtime/gamebotV2Adapter.js)
- [services/mc-mcp/src/runtime/operationScope.js](../../services/mc-mcp/src/runtime/operationScope.js)
- [services/mc-mcp/src/runtime/presentationAnchors.js](../../services/mc-mcp/src/runtime/presentationAnchors.js)
- [services/mc-mcp/src/runtime/presentationPort.js](../../services/mc-mcp/src/runtime/presentationPort.js)
- [services/mc-mcp/src/runtime/processProtocol.js](../../services/mc-mcp/src/runtime/processProtocol.js)

#### services/mc-mcp/src/survival

- [services/mc-mcp/src/survival/inventory.js](../../services/mc-mcp/src/survival/inventory.js)
- [services/mc-mcp/src/survival/phases.js](../../services/mc-mcp/src/survival/phases.js)
- [services/mc-mcp/src/survival/report.js](../../services/mc-mcp/src/survival/report.js)
- [services/mc-mcp/src/survival/runner.js](../../services/mc-mcp/src/survival/runner.js)

#### services/mc-mcp/tests

- [services/mc-mcp/tests/actionDeadline.test.js](../../services/mc-mcp/tests/actionDeadline.test.js)
- [services/mc-mcp/tests/advancementAdapterV2.test.js](../../services/mc-mcp/tests/advancementAdapterV2.test.js)
- [services/mc-mcp/tests/branch_mine.test.js](../../services/mc-mcp/tests/branch_mine.test.js)
- [services/mc-mcp/tests/broadcastMotionPolicy.test.js](../../services/mc-mcp/tests/broadcastMotionPolicy.test.js)
- [services/mc-mcp/tests/clientViewer.test.js](../../services/mc-mcp/tests/clientViewer.test.js)
- [services/mc-mcp/tests/clientViewerController.test.js](../../services/mc-mcp/tests/clientViewerController.test.js)
- [services/mc-mcp/tests/collection.test.js](../../services/mc-mcp/tests/collection.test.js)
- [services/mc-mcp/tests/craftingCounts.test.js](../../services/mc-mcp/tests/craftingCounts.test.js)
- [services/mc-mcp/tests/craftingPlacement.test.js](../../services/mc-mcp/tests/craftingPlacement.test.js)
- [services/mc-mcp/tests/craftingTable.test.js](../../services/mc-mcp/tests/craftingTable.test.js)
- [services/mc-mcp/tests/gamebotAdaptiveEvidenceV2.test.js](../../services/mc-mcp/tests/gamebotAdaptiveEvidenceV2.test.js)
- [services/mc-mcp/tests/gamebotContractV2Parity.test.js](../../services/mc-mcp/tests/gamebotContractV2Parity.test.js)
- [services/mc-mcp/tests/gamebotEvidenceV2.test.js](../../services/mc-mcp/tests/gamebotEvidenceV2.test.js)
- [services/mc-mcp/tests/gamebotRuntimeV2.test.js](../../services/mc-mcp/tests/gamebotRuntimeV2.test.js)
- [services/mc-mcp/tests/gamebotSettlementReplayV2.test.js](../../services/mc-mcp/tests/gamebotSettlementReplayV2.test.js)
- [services/mc-mcp/tests/gamebotV2Adapter.test.js](../../services/mc-mcp/tests/gamebotV2Adapter.test.js)
- [services/mc-mcp/tests/indexCapabilityWiring.test.js](../../services/mc-mcp/tests/indexCapabilityWiring.test.js)
- [services/mc-mcp/tests/mcpCli.test.js](../../services/mc-mcp/tests/mcpCli.test.js)
- [services/mc-mcp/tests/mcpClient.test.js](../../services/mc-mcp/tests/mcpClient.test.js)
- [services/mc-mcp/tests/mcpComposeConfig.test.js](../../services/mc-mcp/tests/mcpComposeConfig.test.js)
- [services/mc-mcp/tests/mcpEventBuffer.test.js](../../services/mc-mcp/tests/mcpEventBuffer.test.js)
- [services/mc-mcp/tests/mcpLifecycle.test.js](../../services/mc-mcp/tests/mcpLifecycle.test.js)
- [services/mc-mcp/tests/mcpProfile.test.js](../../services/mc-mcp/tests/mcpProfile.test.js)
- [services/mc-mcp/tests/mine_shaft.test.js](../../services/mc-mcp/tests/mine_shaft.test.js)
- [services/mc-mcp/tests/operationScope.test.js](../../services/mc-mcp/tests/operationScope.test.js)
- [services/mc-mcp/tests/placement.test.js](../../services/mc-mcp/tests/placement.test.js)
- [services/mc-mcp/tests/presentationAnchors.test.js](../../services/mc-mcp/tests/presentationAnchors.test.js)
- [services/mc-mcp/tests/presentationConfigForwarding.test.js](../../services/mc-mcp/tests/presentationConfigForwarding.test.js)
- [services/mc-mcp/tests/presentationPort.test.js](../../services/mc-mcp/tests/presentationPort.test.js)
- [services/mc-mcp/tests/processProtocol.test.js](../../services/mc-mcp/tests/processProtocol.test.js)
- [services/mc-mcp/tests/resourceLocatorStrategies.test.js](../../services/mc-mcp/tests/resourceLocatorStrategies.test.js)
- [services/mc-mcp/tests/safeChat.test.js](../../services/mc-mcp/tests/safeChat.test.js)
- [services/mc-mcp/tests/secureState.test.js](../../services/mc-mcp/tests/secureState.test.js)
- [services/mc-mcp/tests/smelt.test.js](../../services/mc-mcp/tests/smelt.test.js)

#### services/mc-mcp/tests/survival

- [services/mc-mcp/tests/survival/runner.test.js](../../services/mc-mcp/tests/survival/runner.test.js)

### songs

#### songs

- [songs/.gitignore](../../songs/.gitignore)
- [songs/AGENTS.md](../../songs/AGENTS.md)
- [songs/project.toml](../../songs/project.toml)
- [songs/README.md](../../songs/README.md)

#### songs/audio/dataset/train

- [songs/audio/dataset/train/.gitkeep](../../songs/audio/dataset/train/.gitkeep)

#### songs/audio/dataset/validation

- [songs/audio/dataset/validation/.gitkeep](../../songs/audio/dataset/validation/.gitkeep)

#### songs/audio/processed

- [songs/audio/processed/.gitkeep](../../songs/audio/processed/.gitkeep)

#### songs/audio/raw

- [songs/audio/raw/.gitkeep](../../songs/audio/raw/.gitkeep)

#### songs/evaluation

- [songs/evaluation/protocol.md](../../songs/evaluation/protocol.md)

#### songs/evaluation/audio

- [songs/evaluation/audio/.gitkeep](../../songs/evaluation/audio/.gitkeep)

#### songs/evaluation/renders

- [songs/evaluation/renders/.gitkeep](../../songs/evaluation/renders/.gitkeep)

#### songs/manifests

- [songs/manifests/ab_reviews.csv](../../songs/manifests/ab_reviews.csv)
- [songs/manifests/clips.csv](../../songs/manifests/clips.csv)
- [songs/manifests/evaluation_cases.csv](../../songs/manifests/evaluation_cases.csv)
- [songs/manifests/production_jobs.csv](../../songs/manifests/production_jobs.csv)
- [songs/manifests/sources.csv](../../songs/manifests/sources.csv)
- [songs/manifests/versions.csv](../../songs/manifests/versions.csv)

#### songs/production

- [songs/production/README.md](../../songs/production/README.md)

#### songs/production/converted

- [songs/production/converted/.gitkeep](../../songs/production/converted/.gitkeep)

#### songs/production/exports

- [songs/production/exports/.gitkeep](../../songs/production/exports/.gitkeep)

#### songs/production/phrases

- [songs/production/phrases/.gitkeep](../../songs/production/phrases/.gitkeep)

#### songs/production/sessions

- [songs/production/sessions/.gitkeep](../../songs/production/sessions/.gitkeep)

#### songs/production/source

- [songs/production/source/.gitkeep](../../songs/production/source/.gitkeep)

#### songs/production/stems

- [songs/production/stems/.gitkeep](../../songs/production/stems/.gitkeep)

#### songs/review

- [songs/review/README.md](../../songs/review/README.md) — 未提交

#### songs/runs

- [songs/runs/.gitkeep](../../songs/runs/.gitkeep)

#### songs/templates

- [songs/templates/gpu-probe-evidence.json](../../songs/templates/gpu-probe-evidence.json)

### sources

#### sources

- [sources/research_singing_voice_conversion_hoarseness_20260818.md](../../sources/research_singing_voice_conversion_hoarseness_20260818.md)

#### sources/experiments

- [sources/experiments/singing_voice_method_compare_20260818.md](../../sources/experiments/singing_voice_method_compare_20260818.md)

### src

#### src/animetta

- [src/animetta/__init__.py](../../src/animetta/__init__.py)
- [src/animetta/AGENTS.md](../../src/animetta/AGENTS.md)
- [src/animetta/checkpointing.py](../../src/animetta/checkpointing.py)
- [src/animetta/host_rvc_contract.py](../../src/animetta/host_rvc_contract.py)
- [src/animetta/host_tts_contract.py](../../src/animetta/host_tts_contract.py)
- [src/animetta/socket_event_catalog.py](../../src/animetta/socket_event_catalog.py)

#### src/animetta_qwen_tts

- [src/animetta_qwen_tts/__init__.py](../../src/animetta_qwen_tts/__init__.py)
- [src/animetta_qwen_tts/__main__.py](../../src/animetta_qwen_tts/__main__.py)
- [src/animetta_qwen_tts/app.py](../../src/animetta_qwen_tts/app.py)
- [src/animetta_qwen_tts/gguf_host.py](../../src/animetta_qwen_tts/gguf_host.py)

#### src/animetta_rvc_host

- [src/animetta_rvc_host/__init__.py](../../src/animetta_rvc_host/__init__.py)
- [src/animetta_rvc_host/__main__.py](../../src/animetta_rvc_host/__main__.py)
- [src/animetta_rvc_host/app.py](../../src/animetta_rvc_host/app.py)
- [src/animetta_rvc_host/engine.py](../../src/animetta_rvc_host/engine.py)
- [src/animetta_rvc_host/host.py](../../src/animetta_rvc_host/host.py)
- [src/animetta_rvc_host/separator.py](../../src/animetta_rvc_host/separator.py)

#### src/animetta/acceptance

- [src/animetta/acceptance/__init__.py](../../src/animetta/acceptance/__init__.py)
- [src/animetta/acceptance/conversation_continuity.py](../../src/animetta/acceptance/conversation_continuity.py)
- [src/animetta/acceptance/golden_soak.py](../../src/animetta/acceptance/golden_soak.py)
- [src/animetta/acceptance/live_danmaku_collector.py](../../src/animetta/acceptance/live_danmaku_collector.py)
- [src/animetta/acceptance/minecraft_gameplay_review.py](../../src/animetta/acceptance/minecraft_gameplay_review.py)
- [src/animetta/acceptance/minecraft_showcase.py](../../src/animetta/acceptance/minecraft_showcase.py)
- [src/animetta/acceptance/tts_failover_review.py](../../src/animetta/acceptance/tts_failover_review.py)

#### src/animetta/acceptance/tts_audition

- [src/animetta/acceptance/tts_audition/__init__.py](../../src/animetta/acceptance/tts_audition/__init__.py)
- [src/animetta/acceptance/tts_audition/cli.py](../../src/animetta/acceptance/tts_audition/cli.py)
- [src/animetta/acceptance/tts_audition/clients.py](../../src/animetta/acceptance/tts_audition/clients.py)
- [src/animetta/acceptance/tts_audition/evidence.py](../../src/animetta/acceptance/tts_audition/evidence.py)
- [src/animetta/acceptance/tts_audition/models.py](../../src/animetta/acceptance/tts_audition/models.py)
- [src/animetta/acceptance/tts_audition/plan.py](../../src/animetta/acceptance/tts_audition/plan.py)
- [src/animetta/acceptance/tts_audition/runner.py](../../src/animetta/acceptance/tts_audition/runner.py)

#### src/animetta/avatar

- [src/animetta/avatar/__init__.py](../../src/animetta/avatar/__init__.py)
- [src/animetta/avatar/AGENTS.md](../../src/animetta/avatar/AGENTS.md)
- [src/animetta/avatar/factory.py](../../src/animetta/avatar/factory.py)
- [src/animetta/avatar/performance.py](../../src/animetta/avatar/performance.py)
- [src/animetta/avatar/prompts.py](../../src/animetta/avatar/prompts.py)

#### src/animetta/avatar/analyzers

- [src/animetta/avatar/analyzers/__init__.py](../../src/animetta/avatar/analyzers/__init__.py)
- [src/animetta/avatar/analyzers/audio.py](../../src/animetta/avatar/analyzers/audio.py)
- [src/animetta/avatar/analyzers/base.py](../../src/animetta/avatar/analyzers/base.py)
- [src/animetta/avatar/analyzers/keyword.py](../../src/animetta/avatar/analyzers/keyword.py)
- [src/animetta/avatar/analyzers/llm_tag.py](../../src/animetta/avatar/analyzers/llm_tag.py)

#### src/animetta/avatar/mappers

- [src/animetta/avatar/mappers/__init__.py](../../src/animetta/avatar/mappers/__init__.py)
- [src/animetta/avatar/mappers/base.py](../../src/animetta/avatar/mappers/base.py)
- [src/animetta/avatar/mappers/emotion_param_mapper.py](../../src/animetta/avatar/mappers/emotion_param_mapper.py)

#### src/animetta/avatar/mappers/config

- [src/animetta/avatar/mappers/config/__init__.py](../../src/animetta/avatar/mappers/config/__init__.py)
- [src/animetta/avatar/mappers/config/emotion_mappings.yaml](../../src/animetta/avatar/mappers/config/emotion_mappings.yaml)

#### src/animetta/avatar/strategies

- [src/animetta/avatar/strategies/__init__.py](../../src/animetta/avatar/strategies/__init__.py)
- [src/animetta/avatar/strategies/base.py](../../src/animetta/avatar/strategies/base.py)
- [src/animetta/avatar/strategies/duration.py](../../src/animetta/avatar/strategies/duration.py)
- [src/animetta/avatar/strategies/intensity.py](../../src/animetta/avatar/strategies/intensity.py)
- [src/animetta/avatar/strategies/position.py](../../src/animetta/avatar/strategies/position.py)

#### src/animetta/config

- [src/animetta/config/__init__.py](../../src/animetta/config/__init__.py)
- [src/animetta/config/agent.py](../../src/animetta/config/agent.py)
- [src/animetta/config/AGENTS.md](../../src/animetta/config/AGENTS.md)
- [src/animetta/config/humor.py](../../src/animetta/config/humor.py)
- [src/animetta/config/live2d.py](../../src/animetta/config/live2d.py)
- [src/animetta/config/manifest.py](../../src/animetta/config/manifest.py)
- [src/animetta/config/observability.py](../../src/animetta/config/observability.py)
- [src/animetta/config/proactive_topics.py](../../src/animetta/config/proactive_topics.py)
- [src/animetta/config/runtime_reload.py](../../src/animetta/config/runtime_reload.py)
- [src/animetta/config/runtime_reloader.py](../../src/animetta/config/runtime_reloader.py)
- [src/animetta/config/scene_analysis.py](../../src/animetta/config/scene_analysis.py)
- [src/animetta/config/security.py](../../src/animetta/config/security.py)
- [src/animetta/config/singing.py](../../src/animetta/config/singing.py)
- [src/animetta/config/system.py](../../src/animetta/config/system.py)
- [src/animetta/config/user.py](../../src/animetta/config/user.py)

#### src/animetta/config/core

- [src/animetta/config/core/__init__.py](../../src/animetta/config/core/__init__.py)
- [src/animetta/config/core/base.py](../../src/animetta/config/core/base.py)
- [src/animetta/config/core/mixins.py](../../src/animetta/config/core/mixins.py)
- [src/animetta/config/core/registry.py](../../src/animetta/config/core/registry.py)

#### src/animetta/config/persona

- [src/animetta/config/persona/__init__.py](../../src/animetta/config/persona/__init__.py)
- [src/animetta/config/persona/base.py](../../src/animetta/config/persona/base.py)
- [src/animetta/config/persona/enhanced.py](../../src/animetta/config/persona/enhanced.py)

#### src/animetta/config/providers

- [src/animetta/config/providers/__init__.py](../../src/animetta/config/providers/__init__.py)
- [src/animetta/config/providers/bilibili.py](../../src/animetta/config/providers/bilibili.py)
- [src/animetta/config/providers/earth.py](../../src/animetta/config/providers/earth.py)

#### src/animetta/config/providers/asr

- [src/animetta/config/providers/asr/__init__.py](../../src/animetta/config/providers/asr/__init__.py)
- [src/animetta/config/providers/asr/base.py](../../src/animetta/config/providers/asr/base.py)
- [src/animetta/config/providers/asr/faster_whisper.py](../../src/animetta/config/providers/asr/faster_whisper.py)
- [src/animetta/config/providers/asr/funasr.py](../../src/animetta/config/providers/asr/funasr.py)
- [src/animetta/config/providers/asr/glm.py](../../src/animetta/config/providers/asr/glm.py)
- [src/animetta/config/providers/asr/mimo.py](../../src/animetta/config/providers/asr/mimo.py)
- [src/animetta/config/providers/asr/mock.py](../../src/animetta/config/providers/asr/mock.py)
- [src/animetta/config/providers/asr/openai.py](../../src/animetta/config/providers/asr/openai.py)

#### src/animetta/config/providers/llm

- [src/animetta/config/providers/llm/__init__.py](../../src/animetta/config/providers/llm/__init__.py)
- [src/animetta/config/providers/llm/base.py](../../src/animetta/config/providers/llm/base.py)
- [src/animetta/config/providers/llm/deepseek.py](../../src/animetta/config/providers/llm/deepseek.py)
- [src/animetta/config/providers/llm/glm.py](../../src/animetta/config/providers/llm/glm.py)
- [src/animetta/config/providers/llm/local_lora_llm.py](../../src/animetta/config/providers/llm/local_lora_llm.py)
- [src/animetta/config/providers/llm/mock.py](../../src/animetta/config/providers/llm/mock.py)
- [src/animetta/config/providers/llm/ollama.py](../../src/animetta/config/providers/llm/ollama.py)
- [src/animetta/config/providers/llm/openai.py](../../src/animetta/config/providers/llm/openai.py)
- [src/animetta/config/providers/llm/pricing.py](../../src/animetta/config/providers/llm/pricing.py)

#### src/animetta/config/providers/separation

- [src/animetta/config/providers/separation/__init__.py](../../src/animetta/config/providers/separation/__init__.py)
- [src/animetta/config/providers/separation/base.py](../../src/animetta/config/providers/separation/base.py)
- [src/animetta/config/providers/separation/demucs.py](../../src/animetta/config/providers/separation/demucs.py)
- [src/animetta/config/providers/separation/mock.py](../../src/animetta/config/providers/separation/mock.py)

#### src/animetta/config/providers/tts

- [src/animetta/config/providers/tts/__init__.py](../../src/animetta/config/providers/tts/__init__.py)
- [src/animetta/config/providers/tts/base.py](../../src/animetta/config/providers/tts/base.py)
- [src/animetta/config/providers/tts/chattts.py](../../src/animetta/config/providers/tts/chattts.py)
- [src/animetta/config/providers/tts/dashscope.py](../../src/animetta/config/providers/tts/dashscope.py)
- [src/animetta/config/providers/tts/edge.py](../../src/animetta/config/providers/tts/edge.py)
- [src/animetta/config/providers/tts/failover.py](../../src/animetta/config/providers/tts/failover.py)
- [src/animetta/config/providers/tts/glm.py](../../src/animetta/config/providers/tts/glm.py)
- [src/animetta/config/providers/tts/gpt_sovits.py](../../src/animetta/config/providers/tts/gpt_sovits.py)
- [src/animetta/config/providers/tts/kokoro.py](../../src/animetta/config/providers/tts/kokoro.py)
- [src/animetta/config/providers/tts/mimo.py](../../src/animetta/config/providers/tts/mimo.py)
- [src/animetta/config/providers/tts/mock.py](../../src/animetta/config/providers/tts/mock.py)
- [src/animetta/config/providers/tts/openai.py](../../src/animetta/config/providers/tts/openai.py)
- [src/animetta/config/providers/tts/qwen3.py](../../src/animetta/config/providers/tts/qwen3.py)
- [src/animetta/config/providers/tts/remote.py](../../src/animetta/config/providers/tts/remote.py)
- [src/animetta/config/providers/tts/vibe_voice.py](../../src/animetta/config/providers/tts/vibe_voice.py)

#### src/animetta/config/providers/vad

- [src/animetta/config/providers/vad/__init__.py](../../src/animetta/config/providers/vad/__init__.py)
- [src/animetta/config/providers/vad/base.py](../../src/animetta/config/providers/vad/base.py)
- [src/animetta/config/providers/vad/mimo.py](../../src/animetta/config/providers/vad/mimo.py)
- [src/animetta/config/providers/vad/mock.py](../../src/animetta/config/providers/vad/mock.py)
- [src/animetta/config/providers/vad/silero.py](../../src/animetta/config/providers/vad/silero.py)

#### src/animetta/config/providers/vc

- [src/animetta/config/providers/vc/__init__.py](../../src/animetta/config/providers/vc/__init__.py)
- [src/animetta/config/providers/vc/base.py](../../src/animetta/config/providers/vc/base.py)
- [src/animetta/config/providers/vc/mock.py](../../src/animetta/config/providers/vc/mock.py)
- [src/animetta/config/providers/vc/rvc.py](../../src/animetta/config/providers/vc/rvc.py)

#### src/animetta/core

- [src/animetta/core/__init__.py](../../src/animetta/core/__init__.py)
- [src/animetta/core/AGENTS.md](../../src/animetta/core/AGENTS.md)
- [src/animetta/core/component_readiness.py](../../src/animetta/core/component_readiness.py)
- [src/animetta/core/golden_preflight.py](../../src/animetta/core/golden_preflight.py)
- [src/animetta/core/message_filter.py](../../src/animetta/core/message_filter.py)
- [src/animetta/core/model_loading_manager.py](../../src/animetta/core/model_loading_manager.py)
- [src/animetta/core/readiness.py](../../src/animetta/core/readiness.py)
- [src/animetta/core/redis_checkpoint.py](../../src/animetta/core/redis_checkpoint.py)
- [src/animetta/core/service_context.py](../../src/animetta/core/service_context.py)
- [src/animetta/core/service_pool.py](../../src/animetta/core/service_pool.py)
- [src/animetta/core/shared_memory_runtime.py](../../src/animetta/core/shared_memory_runtime.py)
- [src/animetta/core/socketio_server.py](../../src/animetta/core/socketio_server.py)

#### src/animetta/inspection

- [src/animetta/inspection/__init__.py](../../src/animetta/inspection/__init__.py)
- [src/animetta/inspection/AGENTS.md](../../src/animetta/inspection/AGENTS.md)
- [src/animetta/inspection/inspector.py](../../src/animetta/inspection/inspector.py)
- [src/animetta/inspection/models.py](../../src/animetta/inspection/models.py)
- [src/animetta/inspection/reporter.py](../../src/animetta/inspection/reporter.py)
- [src/animetta/inspection/runtime.py](../../src/animetta/inspection/runtime.py)
- [src/animetta/inspection/scheduler.py](../../src/animetta/inspection/scheduler.py)

#### src/animetta/inspection/checks

- [src/animetta/inspection/checks/__init__.py](../../src/animetta/inspection/checks/__init__.py)
- [src/animetta/inspection/checks/consistency.py](../../src/animetta/inspection/checks/consistency.py)
- [src/animetta/inspection/checks/health.py](../../src/animetta/inspection/checks/health.py)
- [src/animetta/inspection/checks/metrics.py](../../src/animetta/inspection/checks/metrics.py)
- [src/animetta/inspection/checks/pipeline.py](../../src/animetta/inspection/checks/pipeline.py)

#### src/animetta/memory

- [src/animetta/memory/__init__.py](../../src/animetta/memory/__init__.py)
- [src/animetta/memory/AGENTS.md](../../src/animetta/memory/AGENTS.md)

#### src/animetta/memory/v2

- [src/animetta/memory/v2/__init__.py](../../src/animetta/memory/v2/__init__.py)
- [src/animetta/memory/v2/atom.py](../../src/animetta/memory/v2/atom.py)
- [src/animetta/memory/v2/character_filter.py](../../src/animetta/memory/v2/character_filter.py)
- [src/animetta/memory/v2/compile.py](../../src/animetta/memory/v2/compile.py)
- [src/animetta/memory/v2/context.py](../../src/animetta/memory/v2/context.py)
- [src/animetta/memory/v2/emotion_field.py](../../src/animetta/memory/v2/emotion_field.py)
- [src/animetta/memory/v2/metabolism.py](../../src/animetta/memory/v2/metabolism.py)
- [src/animetta/memory/v2/reconsolidation.py](../../src/animetta/memory/v2/reconsolidation.py)
- [src/animetta/memory/v2/search.py](../../src/animetta/memory/v2/search.py)
- [src/animetta/memory/v2/seed_generator.py](../../src/animetta/memory/v2/seed_generator.py)
- [src/animetta/memory/v2/store.py](../../src/animetta/memory/v2/store.py)
- [src/animetta/memory/v2/system.py](../../src/animetta/memory/v2/system.py)

#### src/animetta/notifier

- [src/animetta/notifier/__init__.py](../../src/animetta/notifier/__init__.py)
- [src/animetta/notifier/base.py](../../src/animetta/notifier/base.py)
- [src/animetta/notifier/discord.py](../../src/animetta/notifier/discord.py)
- [src/animetta/notifier/email.py](../../src/animetta/notifier/email.py)
- [src/animetta/notifier/feishu.py](../../src/animetta/notifier/feishu.py)
- [src/animetta/notifier/manager.py](../../src/animetta/notifier/manager.py)
- [src/animetta/notifier/server.py](../../src/animetta/notifier/server.py)

#### src/animetta/notifier/templates

- [src/animetta/notifier/templates/email_alert.html](../../src/animetta/notifier/templates/email_alert.html)

#### src/animetta/observability

- [src/animetta/observability/__init__.py](../../src/animetta/observability/__init__.py)
- [src/animetta/observability/context.py](../../src/animetta/observability/context.py)
- [src/animetta/observability/conversation.py](../../src/animetta/observability/conversation.py)
- [src/animetta/observability/domain.py](../../src/animetta/observability/domain.py)
- [src/animetta/observability/dto.py](../../src/animetta/observability/dto.py)
- [src/animetta/observability/errors.py](../../src/animetta/observability/errors.py)
- [src/animetta/observability/live_dashboard.py](../../src/animetta/observability/live_dashboard.py)
- [src/animetta/observability/operations.py](../../src/animetta/observability/operations.py)
- [src/animetta/observability/ports.py](../../src/animetta/observability/ports.py)
- [src/animetta/observability/privacy.py](../../src/animetta/observability/privacy.py)
- [src/animetta/observability/service_proxy.py](../../src/animetta/observability/service_proxy.py)
- [src/animetta/observability/tts_metrics.py](../../src/animetta/observability/tts_metrics.py)

#### src/animetta/observability/ledger

- [src/animetta/observability/ledger/__init__.py](../../src/animetta/observability/ledger/__init__.py)
- [src/animetta/observability/ledger/sqlite.py](../../src/animetta/observability/ledger/sqlite.py)

#### src/animetta/observability/mirrors

- [src/animetta/observability/mirrors/__init__.py](../../src/animetta/observability/mirrors/__init__.py)
- [src/animetta/observability/mirrors/otel.py](../../src/animetta/observability/mirrors/otel.py)
- [src/animetta/observability/mirrors/prometheus.py](../../src/animetta/observability/mirrors/prometheus.py)

#### src/animetta/orchestration

- [src/animetta/orchestration/__init__.py](../../src/animetta/orchestration/__init__.py)
- [src/animetta/orchestration/AGENTS.md](../../src/animetta/orchestration/AGENTS.md)
- [src/animetta/orchestration/chat_contracts.py](../../src/animetta/orchestration/chat_contracts.py)
- [src/animetta/orchestration/chat_delivery.py](../../src/animetta/orchestration/chat_delivery.py)
- [src/animetta/orchestration/socket_events.py](../../src/animetta/orchestration/socket_events.py)

#### src/animetta/orchestration/graph

- [src/animetta/orchestration/graph/__init__.py](../../src/animetta/orchestration/graph/__init__.py)
- [src/animetta/orchestration/graph/AGENTS.md](../../src/animetta/orchestration/graph/AGENTS.md)
- [src/animetta/orchestration/graph/asr_node.py](../../src/animetta/orchestration/graph/asr_node.py)
- [src/animetta/orchestration/graph/builder.py](../../src/animetta/orchestration/graph/builder.py)
- [src/animetta/orchestration/graph/checkpointing.py](../../src/animetta/orchestration/graph/checkpointing.py)
- [src/animetta/orchestration/graph/conversation_session.py](../../src/animetta/orchestration/graph/conversation_session.py)
- [src/animetta/orchestration/graph/delivery_nodes.py](../../src/animetta/orchestration/graph/delivery_nodes.py)
- [src/animetta/orchestration/graph/dialogue_nodes.py](../../src/animetta/orchestration/graph/dialogue_nodes.py)
- [src/animetta/orchestration/graph/earth_graph.py](../../src/animetta/orchestration/graph/earth_graph.py)
- [src/animetta/orchestration/graph/emotion_node.py](../../src/animetta/orchestration/graph/emotion_node.py)
- [src/animetta/orchestration/graph/humor_rewrite_node.py](../../src/animetta/orchestration/graph/humor_rewrite_node.py)
- [src/animetta/orchestration/graph/humor_utils.py](../../src/animetta/orchestration/graph/humor_utils.py)
- [src/animetta/orchestration/graph/humor_validation_node.py](../../src/animetta/orchestration/graph/humor_validation_node.py)
- [src/animetta/orchestration/graph/instrumentation.py](../../src/animetta/orchestration/graph/instrumentation.py)
- [src/animetta/orchestration/graph/interrupt_handler.py](../../src/animetta/orchestration/graph/interrupt_handler.py)
- [src/animetta/orchestration/graph/llm_node.py](../../src/animetta/orchestration/graph/llm_node.py)
- [src/animetta/orchestration/graph/media_status.py](../../src/animetta/orchestration/graph/media_status.py)
- [src/animetta/orchestration/graph/memory_middleware.py](../../src/animetta/orchestration/graph/memory_middleware.py)
- [src/animetta/orchestration/graph/node_error.py](../../src/animetta/orchestration/graph/node_error.py)
- [src/animetta/orchestration/graph/observability.py](../../src/animetta/orchestration/graph/observability.py)
- [src/animetta/orchestration/graph/orchestrator.py](../../src/animetta/orchestration/graph/orchestrator.py)
- [src/animetta/orchestration/graph/output_node.py](../../src/animetta/orchestration/graph/output_node.py)
- [src/animetta/orchestration/graph/persistence_policy.py](../../src/animetta/orchestration/graph/persistence_policy.py)
- [src/animetta/orchestration/graph/personality_node.py](../../src/animetta/orchestration/graph/personality_node.py)
- [src/animetta/orchestration/graph/scheduler.py](../../src/animetta/orchestration/graph/scheduler.py)
- [src/animetta/orchestration/graph/state.py](../../src/animetta/orchestration/graph/state.py)
- [src/animetta/orchestration/graph/subtitle_translator.py](../../src/animetta/orchestration/graph/subtitle_translator.py)
- [src/animetta/orchestration/graph/tool_execution_policy.py](../../src/animetta/orchestration/graph/tool_execution_policy.py)
- [src/animetta/orchestration/graph/tool_manager.py](../../src/animetta/orchestration/graph/tool_manager.py)
- [src/animetta/orchestration/graph/tool_node.py](../../src/animetta/orchestration/graph/tool_node.py)
- [src/animetta/orchestration/graph/tool_observation.py](../../src/animetta/orchestration/graph/tool_observation.py)
- [src/animetta/orchestration/graph/translation_state.py](../../src/animetta/orchestration/graph/translation_state.py)
- [src/animetta/orchestration/graph/tts_node.py](../../src/animetta/orchestration/graph/tts_node.py)

#### src/animetta/orchestration/prompting

- [src/animetta/orchestration/prompting/__init__.py](../../src/animetta/orchestration/prompting/__init__.py)
- [src/animetta/orchestration/prompting/assembler.py](../../src/animetta/orchestration/prompting/assembler.py)
- [src/animetta/orchestration/prompting/context.py](../../src/animetta/orchestration/prompting/context.py)
- [src/animetta/orchestration/prompting/delivery.py](../../src/animetta/orchestration/prompting/delivery.py)
- [src/animetta/orchestration/prompting/pipeline.py](../../src/animetta/orchestration/prompting/pipeline.py)
- [src/animetta/orchestration/prompting/reasoning_classifier.py](../../src/animetta/orchestration/prompting/reasoning_classifier.py)
- [src/animetta/orchestration/prompting/roleplay_guard.py](../../src/animetta/orchestration/prompting/roleplay_guard.py)
- [src/animetta/orchestration/prompting/sources.py](../../src/animetta/orchestration/prompting/sources.py)
- [src/animetta/orchestration/prompting/types.py](../../src/animetta/orchestration/prompting/types.py)

#### src/animetta/orchestration/server

- [src/animetta/orchestration/server/__init__.py](../../src/animetta/orchestration/server/__init__.py)
- [src/animetta/orchestration/server/auth_admin_cli.py](../../src/animetta/orchestration/server/auth_admin_cli.py)
- [src/animetta/orchestration/server/auth_password.py](../../src/animetta/orchestration/server/auth_password.py)
- [src/animetta/orchestration/server/auth_routes.py](../../src/animetta/orchestration/server/auth_routes.py)
- [src/animetta/orchestration/server/auth_session.py](../../src/animetta/orchestration/server/auth_session.py)
- [src/animetta/orchestration/server/auth_user.py](../../src/animetta/orchestration/server/auth_user.py)
- [src/animetta/orchestration/server/desktop.py](../../src/animetta/orchestration/server/desktop.py)
- [src/animetta/orchestration/server/frontend_health.py](../../src/animetta/orchestration/server/frontend_health.py)
- [src/animetta/orchestration/server/lifecycle.py](../../src/animetta/orchestration/server/lifecycle.py)
- [src/animetta/orchestration/server/live2d.py](../../src/animetta/orchestration/server/live2d.py)
- [src/animetta/orchestration/server/program_script_api.py](../../src/animetta/orchestration/server/program_script_api.py)
- [src/animetta/orchestration/server/routes.py](../../src/animetta/orchestration/server/routes.py)
- [src/animetta/orchestration/server/security.py](../../src/animetta/orchestration/server/security.py)
- [src/animetta/orchestration/server/session.py](../../src/animetta/orchestration/server/session.py)
- [src/animetta/orchestration/server/stats_api.py](../../src/animetta/orchestration/server/stats_api.py)
- [src/animetta/orchestration/server/websocket.py](../../src/animetta/orchestration/server/websocket.py)

#### src/animetta/orchestration/server/handlers

- [src/animetta/orchestration/server/handlers/__init__.py](../../src/animetta/orchestration/server/handlers/__init__.py)
- [src/animetta/orchestration/server/handlers/base_handler.py](../../src/animetta/orchestration/server/handlers/base_handler.py)
- [src/animetta/orchestration/server/handlers/bilibili_handlers.py](../../src/animetta/orchestration/server/handlers/bilibili_handlers.py)
- [src/animetta/orchestration/server/handlers/chat_handlers.py](../../src/animetta/orchestration/server/handlers/chat_handlers.py)
- [src/animetta/orchestration/server/handlers/config_handlers.py](../../src/animetta/orchestration/server/handlers/config_handlers.py)
- [src/animetta/orchestration/server/handlers/earth_handlers.py](../../src/animetta/orchestration/server/handlers/earth_handlers.py)
- [src/animetta/orchestration/server/handlers/lifecycle_handlers.py](../../src/animetta/orchestration/server/handlers/lifecycle_handlers.py)
- [src/animetta/orchestration/server/handlers/live2d_handlers.py](../../src/animetta/orchestration/server/handlers/live2d_handlers.py)
- [src/animetta/orchestration/server/handlers/meme_handlers.py](../../src/animetta/orchestration/server/handlers/meme_handlers.py)
- [src/animetta/orchestration/server/handlers/memory_handlers.py](../../src/animetta/orchestration/server/handlers/memory_handlers.py)
- [src/animetta/orchestration/server/handlers/minecraft_handlers.py](../../src/animetta/orchestration/server/handlers/minecraft_handlers.py)
- [src/animetta/orchestration/server/handlers/persona_handlers.py](../../src/animetta/orchestration/server/handlers/persona_handlers.py)
- [src/animetta/orchestration/server/handlers/singing_handlers.py](../../src/animetta/orchestration/server/handlers/singing_handlers.py)

#### src/animetta/runtime

- [src/animetta/runtime/__init__.py](../../src/animetta/runtime/__init__.py)
- [src/animetta/runtime/checkpoint.py](../../src/animetta/runtime/checkpoint.py)
- [src/animetta/runtime/component_readiness.py](../../src/animetta/runtime/component_readiness.py)
- [src/animetta/runtime/model_loading.py](../../src/animetta/runtime/model_loading.py)
- [src/animetta/runtime/provider_pool.py](../../src/animetta/runtime/provider_pool.py)
- [src/animetta/runtime/readiness.py](../../src/animetta/runtime/readiness.py)
- [src/animetta/runtime/session_context.py](../../src/animetta/runtime/session_context.py)
- [src/animetta/runtime/shared_memory.py](../../src/animetta/runtime/shared_memory.py)

#### src/animetta/services

- [src/animetta/services/__init__.py](../../src/animetta/services/__init__.py)
- [src/animetta/services/AGENTS.md](../../src/animetta/services/AGENTS.md)
- [src/animetta/services/command_inbox.py](../../src/animetta/services/command_inbox.py)
- [src/animetta/services/livestream_narration.py](../../src/animetta/services/livestream_narration.py)
- [src/animetta/services/runtime_config.py](../../src/animetta/services/runtime_config.py)

#### src/animetta/services/asr

- [src/animetta/services/asr/__init__.py](../../src/animetta/services/asr/__init__.py)
- [src/animetta/services/asr/factory.py](../../src/animetta/services/asr/factory.py)
- [src/animetta/services/asr/faster_whisper_asr.py](../../src/animetta/services/asr/faster_whisper_asr.py)
- [src/animetta/services/asr/funasr_asr.py](../../src/animetta/services/asr/funasr_asr.py)
- [src/animetta/services/asr/glm_asr.py](../../src/animetta/services/asr/glm_asr.py)
- [src/animetta/services/asr/interface.py](../../src/animetta/services/asr/interface.py)
- [src/animetta/services/asr/mimo_asr.py](../../src/animetta/services/asr/mimo_asr.py)
- [src/animetta/services/asr/mock_asr.py](../../src/animetta/services/asr/mock_asr.py)

#### src/animetta/services/audio

- [src/animetta/services/audio/__init__.py](../../src/animetta/services/audio/__init__.py)
- [src/animetta/services/audio/processor.py](../../src/animetta/services/audio/processor.py)
- [src/animetta/services/audio/simple_vad_processor.py](../../src/animetta/services/audio/simple_vad_processor.py)
- [src/animetta/services/audio/vad_audio_processor.py](../../src/animetta/services/audio/vad_audio_processor.py)

#### src/animetta/services/bilibili

- [src/animetta/services/bilibili/__init__.py](../../src/animetta/services/bilibili/__init__.py)
- [src/animetta/services/bilibili/api.py](../../src/animetta/services/bilibili/api.py)
- [src/animetta/services/bilibili/danmaku_buffer.py](../../src/animetta/services/bilibili/danmaku_buffer.py)
- [src/animetta/services/bilibili/danmaku_service.py](../../src/animetta/services/bilibili/danmaku_service.py)
- [src/animetta/services/bilibili/event_normalizer.py](../../src/animetta/services/bilibili/event_normalizer.py)
- [src/animetta/services/bilibili/gateway.py](../../src/animetta/services/bilibili/gateway.py)
- [src/animetta/services/bilibili/interaction_learner.py](../../src/animetta/services/bilibili/interaction_learner.py)
- [src/animetta/services/bilibili/livestream_session.py](../../src/animetta/services/bilibili/livestream_session.py)
- [src/animetta/services/bilibili/livestream_state.py](../../src/animetta/services/bilibili/livestream_state.py)
- [src/animetta/services/bilibili/meme_collector.py](../../src/animetta/services/bilibili/meme_collector.py)
- [src/animetta/services/bilibili/meme_prompts.py](../../src/animetta/services/bilibili/meme_prompts.py)
- [src/animetta/services/bilibili/meme_utils.py](../../src/animetta/services/bilibili/meme_utils.py)
- [src/animetta/services/bilibili/models.py](../../src/animetta/services/bilibili/models.py)
- [src/animetta/services/bilibili/proactive_topics.py](../../src/animetta/services/bilibili/proactive_topics.py)
- [src/animetta/services/bilibili/replay_gateway.py](../../src/animetta/services/bilibili/replay_gateway.py)
- [src/animetta/services/bilibili/reply_admission.py](../../src/animetta/services/bilibili/reply_admission.py)
- [src/animetta/services/bilibili/reply_media.py](../../src/animetta/services/bilibili/reply_media.py)
- [src/animetta/services/bilibili/reply_queue.py](../../src/animetta/services/bilibili/reply_queue.py)
- [src/animetta/services/bilibili/response_policy.py](../../src/animetta/services/bilibili/response_policy.py)
- [src/animetta/services/bilibili/text_utils.py](../../src/animetta/services/bilibili/text_utils.py)

#### src/animetta/services/dialogue

- [src/animetta/services/dialogue/__init__.py](../../src/animetta/services/dialogue/__init__.py)
- [src/animetta/services/dialogue/contracts.py](../../src/animetta/services/dialogue/contracts.py)
- [src/animetta/services/dialogue/guard.py](../../src/animetta/services/dialogue/guard.py)
- [src/animetta/services/dialogue/message_filter.py](../../src/animetta/services/dialogue/message_filter.py)
- [src/animetta/services/dialogue/models.py](../../src/animetta/services/dialogue/models.py)
- [src/animetta/services/dialogue/prompts.py](../../src/animetta/services/dialogue/prompts.py)
- [src/animetta/services/dialogue/reasoning_classifier.py](../../src/animetta/services/dialogue/reasoning_classifier.py)
- [src/animetta/services/dialogue/response_processing.py](../../src/animetta/services/dialogue/response_processing.py)
- [src/animetta/services/dialogue/roleplay_guard.py](../../src/animetta/services/dialogue/roleplay_guard.py)
- [src/animetta/services/dialogue/sandbox.py](../../src/animetta/services/dialogue/sandbox.py)
- [src/animetta/services/dialogue/services.py](../../src/animetta/services/dialogue/services.py)

#### src/animetta/services/earth

- [src/animetta/services/earth/__init__.py](../../src/animetta/services/earth/__init__.py)
- [src/animetta/services/earth/audio.py](../../src/animetta/services/earth/audio.py)
- [src/animetta/services/earth/contracts.py](../../src/animetta/services/earth/contracts.py)
- [src/animetta/services/earth/domain.py](../../src/animetta/services/earth/domain.py)
- [src/animetta/services/earth/exploration.py](../../src/animetta/services/earth/exploration.py)
- [src/animetta/services/earth/factory.py](../../src/animetta/services/earth/factory.py)
- [src/animetta/services/earth/interface.py](../../src/animetta/services/earth/interface.py)
- [src/animetta/services/earth/photon.py](../../src/animetta/services/earth/photon.py)

#### src/animetta/services/effects

- [src/animetta/services/effects/__init__.py](../../src/animetta/services/effects/__init__.py)
- [src/animetta/services/effects/runtime.py](../../src/animetta/services/effects/runtime.py)

#### src/animetta/services/humor

- [src/animetta/services/humor/__init__.py](../../src/animetta/services/humor/__init__.py)
- [src/animetta/services/humor/agent.py](../../src/animetta/services/humor/agent.py)
- [src/animetta/services/humor/config.py](../../src/animetta/services/humor/config.py)
- [src/animetta/services/humor/filters.py](../../src/animetta/services/humor/filters.py)
- [src/animetta/services/humor/history_safe.py](../../src/animetta/services/humor/history_safe.py)
- [src/animetta/services/humor/metadata.py](../../src/animetta/services/humor/metadata.py)
- [src/animetta/services/humor/models.py](../../src/animetta/services/humor/models.py)
- [src/animetta/services/humor/parser.py](../../src/animetta/services/humor/parser.py)
- [src/animetta/services/humor/prompts.py](../../src/animetta/services/humor/prompts.py)

#### src/animetta/services/live2d

- [src/animetta/services/live2d/__init__.py](../../src/animetta/services/live2d/__init__.py)
- [src/animetta/services/live2d/action_queue.py](../../src/animetta/services/live2d/action_queue.py)
- [src/animetta/services/live2d/preset_loader.py](../../src/animetta/services/live2d/preset_loader.py)
- [src/animetta/services/live2d/viseme_sync.py](../../src/animetta/services/live2d/viseme_sync.py)

#### src/animetta/services/llm

- [src/animetta/services/llm/__init__.py](../../src/animetta/services/llm/__init__.py)
- [src/animetta/services/llm/deepseek_policy.py](../../src/animetta/services/llm/deepseek_policy.py)
- [src/animetta/services/llm/factory.py](../../src/animetta/services/llm/factory.py)
- [src/animetta/services/llm/glm_llm.py](../../src/animetta/services/llm/glm_llm.py)
- [src/animetta/services/llm/glm_message_converter.py](../../src/animetta/services/llm/glm_message_converter.py)
- [src/animetta/services/llm/interface.py](../../src/animetta/services/llm/interface.py)
- [src/animetta/services/llm/internal_calls.py](../../src/animetta/services/llm/internal_calls.py)
- [src/animetta/services/llm/langchain_adapter.py](../../src/animetta/services/llm/langchain_adapter.py)
- [src/animetta/services/llm/local_lora_llm.py](../../src/animetta/services/llm/local_lora_llm.py)
- [src/animetta/services/llm/minecraft_tool_policy.py](../../src/animetta/services/llm/minecraft_tool_policy.py)
- [src/animetta/services/llm/mock_llm.py](../../src/animetta/services/llm/mock_llm.py)
- [src/animetta/services/llm/ollama_llm.py](../../src/animetta/services/llm/ollama_llm.py)
- [src/animetta/services/llm/openai_llm.py](../../src/animetta/services/llm/openai_llm.py)
- [src/animetta/services/llm/stream_handler.py](../../src/animetta/services/llm/stream_handler.py)
- [src/animetta/services/llm/token_counting.py](../../src/animetta/services/llm/token_counting.py)
- [src/animetta/services/llm/tool_handler.py](../../src/animetta/services/llm/tool_handler.py)
- [src/animetta/services/llm/usage.py](../../src/animetta/services/llm/usage.py)

#### src/animetta/services/meme

- [src/animetta/services/meme/__init__.py](../../src/animetta/services/meme/__init__.py)
- [src/animetta/services/meme/analyzer.py](../../src/animetta/services/meme/analyzer.py)
- [src/animetta/services/meme/styles.py](../../src/animetta/services/meme/styles.py)

#### src/animetta/services/program_script

- [src/animetta/services/program_script/__init__.py](../../src/animetta/services/program_script/__init__.py)
- [src/animetta/services/program_script/models.py](../../src/animetta/services/program_script/models.py)
- [src/animetta/services/program_script/replay.py](../../src/animetta/services/program_script/replay.py)
- [src/animetta/services/program_script/repository.py](../../src/animetta/services/program_script/repository.py)
- [src/animetta/services/program_script/runtime.py](../../src/animetta/services/program_script/runtime.py)

#### src/animetta/services/scene_analysis

- [src/animetta/services/scene_analysis/__init__.py](../../src/animetta/services/scene_analysis/__init__.py)
- [src/animetta/services/scene_analysis/evidence.py](../../src/animetta/services/scene_analysis/evidence.py)
- [src/animetta/services/scene_analysis/guidance.py](../../src/animetta/services/scene_analysis/guidance.py)
- [src/animetta/services/scene_analysis/model_gateway.py](../../src/animetta/services/scene_analysis/model_gateway.py)
- [src/animetta/services/scene_analysis/models.py](../../src/animetta/services/scene_analysis/models.py)
- [src/animetta/services/scene_analysis/reducer.py](../../src/animetta/services/scene_analysis/reducer.py)
- [src/animetta/services/scene_analysis/runtime.py](../../src/animetta/services/scene_analysis/runtime.py)
- [src/animetta/services/scene_analysis/validation.py](../../src/animetta/services/scene_analysis/validation.py)

#### src/animetta/services/separation

- [src/animetta/services/separation/__init__.py](../../src/animetta/services/separation/__init__.py)
- [src/animetta/services/separation/factory.py](../../src/animetta/services/separation/factory.py)
- [src/animetta/services/separation/interface.py](../../src/animetta/services/separation/interface.py)
- [src/animetta/services/separation/mock_separation.py](../../src/animetta/services/separation/mock_separation.py)

#### src/animetta/services/singing

- [src/animetta/services/singing/__init__.py](../../src/animetta/services/singing/__init__.py)
- [src/animetta/services/singing/bilibili.py](../../src/animetta/services/singing/bilibili.py)
- [src/animetta/services/singing/interface.py](../../src/animetta/services/singing/interface.py)
- [src/animetta/services/singing/lyrics.py](../../src/animetta/services/singing/lyrics.py)
- [src/animetta/services/singing/mixer.py](../../src/animetta/services/singing/mixer.py)
- [src/animetta/services/singing/rvc_bridge.py](../../src/animetta/services/singing/rvc_bridge.py)
- [src/animetta/services/singing/separator.py](../../src/animetta/services/singing/separator.py)
- [src/animetta/services/singing/svc_bridge.py](../../src/animetta/services/singing/svc_bridge.py)
- [src/animetta/services/singing/svc_pipeline.py](../../src/animetta/services/singing/svc_pipeline.py)

#### src/animetta/services/tts

- [src/animetta/services/tts/__init__.py](../../src/animetta/services/tts/__init__.py)
- [src/animetta/services/tts/audio_validation.py](../../src/animetta/services/tts/audio_validation.py)
- [src/animetta/services/tts/dashscope_tts.py](../../src/animetta/services/tts/dashscope_tts.py)
- [src/animetta/services/tts/edge_tts.py](../../src/animetta/services/tts/edge_tts.py)
- [src/animetta/services/tts/emotion_instructions.py](../../src/animetta/services/tts/emotion_instructions.py)
- [src/animetta/services/tts/factory.py](../../src/animetta/services/tts/factory.py)
- [src/animetta/services/tts/failover_tts.py](../../src/animetta/services/tts/failover_tts.py)
- [src/animetta/services/tts/gpt_sovits_tts.py](../../src/animetta/services/tts/gpt_sovits_tts.py)
- [src/animetta/services/tts/interface.py](../../src/animetta/services/tts/interface.py)
- [src/animetta/services/tts/mimo_tts.py](../../src/animetta/services/tts/mimo_tts.py)
- [src/animetta/services/tts/mock_tts.py](../../src/animetta/services/tts/mock_tts.py)
- [src/animetta/services/tts/qwen3_tts.py](../../src/animetta/services/tts/qwen3_tts.py)
- [src/animetta/services/tts/remote_tts.py](../../src/animetta/services/tts/remote_tts.py)
- [src/animetta/services/tts/streaming.py](../../src/animetta/services/tts/streaming.py)

#### src/animetta/services/tts/contrib

- [src/animetta/services/tts/contrib/__init__.py](../../src/animetta/services/tts/contrib/__init__.py)
- [src/animetta/services/tts/contrib/chattts_tts.py](../../src/animetta/services/tts/contrib/chattts_tts.py)
- [src/animetta/services/tts/contrib/glados_effect.py](../../src/animetta/services/tts/contrib/glados_effect.py)
- [src/animetta/services/tts/contrib/glm_tts.py](../../src/animetta/services/tts/contrib/glm_tts.py)
- [src/animetta/services/tts/contrib/kokoro_tts.py](../../src/animetta/services/tts/contrib/kokoro_tts.py)
- [src/animetta/services/tts/contrib/vibe_voice_tts.py](../../src/animetta/services/tts/contrib/vibe_voice_tts.py)

#### src/animetta/services/vad

- [src/animetta/services/vad/__init__.py](../../src/animetta/services/vad/__init__.py)
- [src/animetta/services/vad/detector.py](../../src/animetta/services/vad/detector.py)
- [src/animetta/services/vad/factory.py](../../src/animetta/services/vad/factory.py)
- [src/animetta/services/vad/interface.py](../../src/animetta/services/vad/interface.py)
- [src/animetta/services/vad/mimo_vad.py](../../src/animetta/services/vad/mimo_vad.py)
- [src/animetta/services/vad/mock_vad.py](../../src/animetta/services/vad/mock_vad.py)
- [src/animetta/services/vad/silero_vad.py](../../src/animetta/services/vad/silero_vad.py)

#### src/animetta/services/vc

- [src/animetta/services/vc/__init__.py](../../src/animetta/services/vc/__init__.py)
- [src/animetta/services/vc/factory.py](../../src/animetta/services/vc/factory.py)
- [src/animetta/services/vc/interface.py](../../src/animetta/services/vc/interface.py)
- [src/animetta/services/vc/mock_vc.py](../../src/animetta/services/vc/mock_vc.py)
- [src/animetta/services/vc/rvc_vc.py](../../src/animetta/services/vc/rvc_vc.py)

#### src/animetta/tools

- [src/animetta/tools/__init__.py](../../src/animetta/tools/__init__.py)
- [src/animetta/tools/AGENTS.md](../../src/animetta/tools/AGENTS.md)
- [src/animetta/tools/base.py](../../src/animetta/tools/base.py)
- [src/animetta/tools/custom_tools.py](../../src/animetta/tools/custom_tools.py)
- [src/animetta/tools/langchain_tools.py](../../src/animetta/tools/langchain_tools.py)
- [src/animetta/tools/mcp_bridge.py](../../src/animetta/tools/mcp_bridge.py)

#### src/animetta/tools/earth

- [src/animetta/tools/earth/__init__.py](../../src/animetta/tools/earth/__init__.py)

#### src/animetta/tools/gamebot

- [src/animetta/tools/gamebot/__init__.py](../../src/animetta/tools/gamebot/__init__.py)
- [src/animetta/tools/gamebot/client.py](../../src/animetta/tools/gamebot/client.py)
- [src/animetta/tools/gamebot/runtime.py](../../src/animetta/tools/gamebot/runtime.py)
- [src/animetta/tools/gamebot/state_collector.py](../../src/animetta/tools/gamebot/state_collector.py)
- [src/animetta/tools/gamebot/stdio_transport.py](../../src/animetta/tools/gamebot/stdio_transport.py)
- [src/animetta/tools/gamebot/tools.py](../../src/animetta/tools/gamebot/tools.py)
- [src/animetta/tools/gamebot/transport.py](../../src/animetta/tools/gamebot/transport.py)

#### src/animetta/tools/gamebot/contracts

- [src/animetta/tools/gamebot/contracts/__init__.py](../../src/animetta/tools/gamebot/contracts/__init__.py)
- [src/animetta/tools/gamebot/contracts/commands.py](../../src/animetta/tools/gamebot/contracts/commands.py)
- [src/animetta/tools/gamebot/contracts/errors.py](../../src/animetta/tools/gamebot/contracts/errors.py)
- [src/animetta/tools/gamebot/contracts/events.py](../../src/animetta/tools/gamebot/contracts/events.py)
- [src/animetta/tools/gamebot/contracts/status.py](../../src/animetta/tools/gamebot/contracts/status.py)
- [src/animetta/tools/gamebot/contracts/voyager.py](../../src/animetta/tools/gamebot/contracts/voyager.py)

#### src/animetta/tools/gamebot/contracts/v2

- [src/animetta/tools/gamebot/contracts/v2/__init__.py](../../src/animetta/tools/gamebot/contracts/v2/__init__.py)
- [src/animetta/tools/gamebot/contracts/v2/_base.py](../../src/animetta/tools/gamebot/contracts/v2/_base.py)
- [src/animetta/tools/gamebot/contracts/v2/budget.py](../../src/animetta/tools/gamebot/contracts/v2/budget.py)
- [src/animetta/tools/gamebot/contracts/v2/errors.py](../../src/animetta/tools/gamebot/contracts/v2/errors.py)
- [src/animetta/tools/gamebot/contracts/v2/evidence.py](../../src/animetta/tools/gamebot/contracts/v2/evidence.py)
- [src/animetta/tools/gamebot/contracts/v2/manifest.py](../../src/animetta/tools/gamebot/contracts/v2/manifest.py)
- [src/animetta/tools/gamebot/contracts/v2/observations.py](../../src/animetta/tools/gamebot/contracts/v2/observations.py)
- [src/animetta/tools/gamebot/contracts/v2/receipts.py](../../src/animetta/tools/gamebot/contracts/v2/receipts.py)
- [src/animetta/tools/gamebot/contracts/v2/requests.py](../../src/animetta/tools/gamebot/contracts/v2/requests.py)
- [src/animetta/tools/gamebot/contracts/v2/schema.py](../../src/animetta/tools/gamebot/contracts/v2/schema.py)

#### src/animetta/tools/minecraft

- [src/animetta/tools/minecraft/__init__.py](../../src/animetta/tools/minecraft/__init__.py)
- [src/animetta/tools/minecraft/AGENTS.md](../../src/animetta/tools/minecraft/AGENTS.md)
- [src/animetta/tools/minecraft/rules.md](../../src/animetta/tools/minecraft/rules.md)

#### src/animetta/tools/minecraft/autonomous

- [src/animetta/tools/minecraft/autonomous/__init__.py](../../src/animetta/tools/minecraft/autonomous/__init__.py)
- [src/animetta/tools/minecraft/autonomous/curriculum.py](../../src/animetta/tools/minecraft/autonomous/curriculum.py)
- [src/animetta/tools/minecraft/autonomous/planner.py](../../src/animetta/tools/minecraft/autonomous/planner.py)
- [src/animetta/tools/minecraft/autonomous/rules_engine.py](../../src/animetta/tools/minecraft/autonomous/rules_engine.py)
- [src/animetta/tools/minecraft/autonomous/training.py](../../src/animetta/tools/minecraft/autonomous/training.py)

#### src/animetta/tools/minecraft/benchmark

- [src/animetta/tools/minecraft/benchmark/__init__.py](../../src/animetta/tools/minecraft/benchmark/__init__.py)
- [src/animetta/tools/minecraft/benchmark/criteria.py](../../src/animetta/tools/minecraft/benchmark/criteria.py)
- [src/animetta/tools/minecraft/benchmark/main.py](../../src/animetta/tools/minecraft/benchmark/main.py)
- [src/animetta/tools/minecraft/benchmark/models.py](../../src/animetta/tools/minecraft/benchmark/models.py)
- [src/animetta/tools/minecraft/benchmark/report.py](../../src/animetta/tools/minecraft/benchmark/report.py)
- [src/animetta/tools/minecraft/benchmark/scenarios.py](../../src/animetta/tools/minecraft/benchmark/scenarios.py)

#### src/animetta/tools/minecraft/blueprint

- [src/animetta/tools/minecraft/blueprint/__init__.py](../../src/animetta/tools/minecraft/blueprint/__init__.py)
- [src/animetta/tools/minecraft/blueprint/compiler.py](../../src/animetta/tools/minecraft/blueprint/compiler.py)
- [src/animetta/tools/minecraft/blueprint/models.py](../../src/animetta/tools/minecraft/blueprint/models.py)
- [src/animetta/tools/minecraft/blueprint/starter.py](../../src/animetta/tools/minecraft/blueprint/starter.py)
- [src/animetta/tools/minecraft/blueprint/verifier.py](../../src/animetta/tools/minecraft/blueprint/verifier.py)

#### src/animetta/tools/minecraft/core

- [src/animetta/tools/minecraft/core/__init__.py](../../src/animetta/tools/minecraft/core/__init__.py)
- [src/animetta/tools/minecraft/core/adapter.py](../../src/animetta/tools/minecraft/core/adapter.py)
- [src/animetta/tools/minecraft/core/assembly.py](../../src/animetta/tools/minecraft/core/assembly.py)
- [src/animetta/tools/minecraft/core/bridge.py](../../src/animetta/tools/minecraft/core/bridge.py)
- [src/animetta/tools/minecraft/core/config.py](../../src/animetta/tools/minecraft/core/config.py)
- [src/animetta/tools/minecraft/core/tools.py](../../src/animetta/tools/minecraft/core/tools.py)

#### src/animetta/tools/minecraft/demo

- [src/animetta/tools/minecraft/demo/__init__.py](../../src/animetta/tools/minecraft/demo/__init__.py)
- [src/animetta/tools/minecraft/demo/__main__.py](../../src/animetta/tools/minecraft/demo/__main__.py)
- [src/animetta/tools/minecraft/demo/cli.py](../../src/animetta/tools/minecraft/demo/cli.py)
- [src/animetta/tools/minecraft/demo/scenario.py](../../src/animetta/tools/minecraft/demo/scenario.py)

#### src/animetta/tools/minecraft/discovery

- [src/animetta/tools/minecraft/discovery/__init__.py](../../src/animetta/tools/minecraft/discovery/__init__.py)
- [src/animetta/tools/minecraft/discovery/exploration.py](../../src/animetta/tools/minecraft/discovery/exploration.py)
- [src/animetta/tools/minecraft/discovery/models.py](../../src/animetta/tools/minecraft/discovery/models.py)
- [src/animetta/tools/minecraft/discovery/projector.py](../../src/animetta/tools/minecraft/discovery/projector.py)
- [src/animetta/tools/minecraft/discovery/runtime.py](../../src/animetta/tools/minecraft/discovery/runtime.py)
- [src/animetta/tools/minecraft/discovery/store.py](../../src/animetta/tools/minecraft/discovery/store.py)

#### src/animetta/tools/minecraft/mission

- [src/animetta/tools/minecraft/mission/__init__.py](../../src/animetta/tools/minecraft/mission/__init__.py)
- [src/animetta/tools/minecraft/mission/adaptive.py](../../src/animetta/tools/minecraft/mission/adaptive.py)
- [src/animetta/tools/minecraft/mission/admission.py](../../src/animetta/tools/minecraft/mission/admission.py)
- [src/animetta/tools/minecraft/mission/coordinator.py](../../src/animetta/tools/minecraft/mission/coordinator.py)
- [src/animetta/tools/minecraft/mission/events.py](../../src/animetta/tools/minecraft/mission/events.py)
- [src/animetta/tools/minecraft/mission/models.py](../../src/animetta/tools/minecraft/mission/models.py)
- [src/animetta/tools/minecraft/mission/projection.py](../../src/animetta/tools/minecraft/mission/projection.py)
- [src/animetta/tools/minecraft/mission/repository.py](../../src/animetta/tools/minecraft/mission/repository.py)
- [src/animetta/tools/minecraft/mission/runtime.py](../../src/animetta/tools/minecraft/mission/runtime.py)
- [src/animetta/tools/minecraft/mission/schema.py](../../src/animetta/tools/minecraft/mission/schema.py)
- [src/animetta/tools/minecraft/mission/state_machine.py](../../src/animetta/tools/minecraft/mission/state_machine.py)
- [src/animetta/tools/minecraft/mission/verifier.py](../../src/animetta/tools/minecraft/mission/verifier.py)

#### src/animetta/tools/minecraft/other

- [src/animetta/tools/minecraft/other/__init__.py](../../src/animetta/tools/minecraft/other/__init__.py)
- [src/animetta/tools/minecraft/other/trace_recorder.py](../../src/animetta/tools/minecraft/other/trace_recorder.py)
- [src/animetta/tools/minecraft/other/world_state.py](../../src/animetta/tools/minecraft/other/world_state.py)

#### src/animetta/tools/minecraft/showcase

- [src/animetta/tools/minecraft/showcase/__init__.py](../../src/animetta/tools/minecraft/showcase/__init__.py)
- [src/animetta/tools/minecraft/showcase/dialogue_regression.py](../../src/animetta/tools/minecraft/showcase/dialogue_regression.py)
- [src/animetta/tools/minecraft/showcase/historical_audit.py](../../src/animetta/tools/minecraft/showcase/historical_audit.py)
- [src/animetta/tools/minecraft/showcase/live.py](../../src/animetta/tools/minecraft/showcase/live.py)
- [src/animetta/tools/minecraft/showcase/micro_gates.py](../../src/animetta/tools/minecraft/showcase/micro_gates.py)
- [src/animetta/tools/minecraft/showcase/presentation.py](../../src/animetta/tools/minecraft/showcase/presentation.py)
- [src/animetta/tools/minecraft/showcase/projection_relay.py](../../src/animetta/tools/minecraft/showcase/projection_relay.py)
- [src/animetta/tools/minecraft/showcase/promotion.py](../../src/animetta/tools/minecraft/showcase/promotion.py)
- [src/animetta/tools/minecraft/showcase/runner.py](../../src/animetta/tools/minecraft/showcase/runner.py)
- [src/animetta/tools/minecraft/showcase/scenario.py](../../src/animetta/tools/minecraft/showcase/scenario.py)
- [src/animetta/tools/minecraft/showcase/stage_projector.py](../../src/animetta/tools/minecraft/showcase/stage_projector.py)

#### src/animetta/tools/minecraft/skill

- [src/animetta/tools/minecraft/skill/__init__.py](../../src/animetta/tools/minecraft/skill/__init__.py)
- [src/animetta/tools/minecraft/skill/applicability.py](../../src/animetta/tools/minecraft/skill/applicability.py)
- [src/animetta/tools/minecraft/skill/catalog.py](../../src/animetta/tools/minecraft/skill/catalog.py)
- [src/animetta/tools/minecraft/skill/conditions.py](../../src/animetta/tools/minecraft/skill/conditions.py)
- [src/animetta/tools/minecraft/skill/extractor.py](../../src/animetta/tools/minecraft/skill/extractor.py)
- [src/animetta/tools/minecraft/skill/independent_validation.py](../../src/animetta/tools/minecraft/skill/independent_validation.py)
- [src/animetta/tools/minecraft/skill/ir.py](../../src/animetta/tools/minecraft/skill/ir.py)
- [src/animetta/tools/minecraft/skill/library.py](../../src/animetta/tools/minecraft/skill/library.py)
- [src/animetta/tools/minecraft/skill/models.py](../../src/animetta/tools/minecraft/skill/models.py)
- [src/animetta/tools/minecraft/skill/predefined.py](../../src/animetta/tools/minecraft/skill/predefined.py)
- [src/animetta/tools/minecraft/skill/revision_store.py](../../src/animetta/tools/minecraft/skill/revision_store.py)
- [src/animetta/tools/minecraft/skill/selection.py](../../src/animetta/tools/minecraft/skill/selection.py)
- [src/animetta/tools/minecraft/skill/store.py](../../src/animetta/tools/minecraft/skill/store.py)
- [src/animetta/tools/minecraft/skill/trust.py](../../src/animetta/tools/minecraft/skill/trust.py)
- [src/animetta/tools/minecraft/skill/validator.py](../../src/animetta/tools/minecraft/skill/validator.py)
- [src/animetta/tools/minecraft/skill/verifier.py](../../src/animetta/tools/minecraft/skill/verifier.py)

#### src/animetta/tools/minecraft/survival

- [src/animetta/tools/minecraft/survival/__init__.py](../../src/animetta/tools/minecraft/survival/__init__.py)
- [src/animetta/tools/minecraft/survival/benchmark.py](../../src/animetta/tools/minecraft/survival/benchmark.py)
- [src/animetta/tools/minecraft/survival/inventory.py](../../src/animetta/tools/minecraft/survival/inventory.py)
- [src/animetta/tools/minecraft/survival/models.py](../../src/animetta/tools/minecraft/survival/models.py)
- [src/animetta/tools/minecraft/survival/recovery.py](../../src/animetta/tools/minecraft/survival/recovery.py)
- [src/animetta/tools/minecraft/survival/registry.py](../../src/animetta/tools/minecraft/survival/registry.py)
- [src/animetta/tools/minecraft/survival/SKILLS.md](../../src/animetta/tools/minecraft/survival/SKILLS.md)
- [src/animetta/tools/minecraft/survival/workflows.py](../../src/animetta/tools/minecraft/survival/workflows.py)

#### src/animetta/tools/minecraft/tech_tree

- [src/animetta/tools/minecraft/tech_tree/__init__.py](../../src/animetta/tools/minecraft/tech_tree/__init__.py)
- [src/animetta/tools/minecraft/tech_tree/adapter.py](../../src/animetta/tools/minecraft/tech_tree/adapter.py)
- [src/animetta/tools/minecraft/tech_tree/defaults.py](../../src/animetta/tools/minecraft/tech_tree/defaults.py)
- [src/animetta/tools/minecraft/tech_tree/graph.py](../../src/animetta/tools/minecraft/tech_tree/graph.py)
- [src/animetta/tools/minecraft/tech_tree/main.py](../../src/animetta/tools/minecraft/tech_tree/main.py)
- [src/animetta/tools/minecraft/tech_tree/models.py](../../src/animetta/tools/minecraft/tech_tree/models.py)
- [src/animetta/tools/minecraft/tech_tree/report.py](../../src/animetta/tools/minecraft/tech_tree/report.py)

#### src/animetta/tools/minecraft/voyager

- [src/animetta/tools/minecraft/voyager/__init__.py](../../src/animetta/tools/minecraft/voyager/__init__.py)
- [src/animetta/tools/minecraft/voyager/advancement_store.py](../../src/animetta/tools/minecraft/voyager/advancement_store.py)
- [src/animetta/tools/minecraft/voyager/budget.py](../../src/animetta/tools/minecraft/voyager/budget.py)
- [src/animetta/tools/minecraft/voyager/command_executor.py](../../src/animetta/tools/minecraft/voyager/command_executor.py)
- [src/animetta/tools/minecraft/voyager/command_models.py](../../src/animetta/tools/minecraft/voyager/command_models.py)
- [src/animetta/tools/minecraft/voyager/control_plane.py](../../src/animetta/tools/minecraft/voyager/control_plane.py)
- [src/animetta/tools/minecraft/voyager/events.py](../../src/animetta/tools/minecraft/voyager/events.py)
- [src/animetta/tools/minecraft/voyager/faults.py](../../src/animetta/tools/minecraft/voyager/faults.py)
- [src/animetta/tools/minecraft/voyager/gateway.py](../../src/animetta/tools/minecraft/voyager/gateway.py)
- [src/animetta/tools/minecraft/voyager/goal_evidence.py](../../src/animetta/tools/minecraft/voyager/goal_evidence.py)
- [src/animetta/tools/minecraft/voyager/goal_models.py](../../src/animetta/tools/minecraft/voyager/goal_models.py)
- [src/animetta/tools/minecraft/voyager/goal_verifier.py](../../src/animetta/tools/minecraft/voyager/goal_verifier.py)
- [src/animetta/tools/minecraft/voyager/journal.py](../../src/animetta/tools/minecraft/voyager/journal.py)
- [src/animetta/tools/minecraft/voyager/public_activity.py](../../src/animetta/tools/minecraft/voyager/public_activity.py)
- [src/animetta/tools/minecraft/voyager/reconciliation.py](../../src/animetta/tools/minecraft/voyager/reconciliation.py)
- [src/animetta/tools/minecraft/voyager/scheduler.py](../../src/animetta/tools/minecraft/voyager/scheduler.py)
- [src/animetta/tools/minecraft/voyager/sqlite_repository.py](../../src/animetta/tools/minecraft/voyager/sqlite_repository.py)
- [src/animetta/tools/minecraft/voyager/stop.py](../../src/animetta/tools/minecraft/voyager/stop.py)

#### src/animetta/tools/minecraft/voyager/strategies

- [src/animetta/tools/minecraft/voyager/strategies/__init__.py](../../src/animetta/tools/minecraft/voyager/strategies/__init__.py)
- [src/animetta/tools/minecraft/voyager/strategies/atomic.py](../../src/animetta/tools/minecraft/voyager/strategies/atomic.py)
- [src/animetta/tools/minecraft/voyager/strategies/base.py](../../src/animetta/tools/minecraft/voyager/strategies/base.py)
- [src/animetta/tools/minecraft/voyager/strategies/builtin.py](../../src/animetta/tools/minecraft/voyager/strategies/builtin.py)
- [src/animetta/tools/minecraft/voyager/strategies/fallback.py](../../src/animetta/tools/minecraft/voyager/strategies/fallback.py)
- [src/animetta/tools/minecraft/voyager/strategies/learn.py](../../src/animetta/tools/minecraft/voyager/strategies/learn.py)
- [src/animetta/tools/minecraft/voyager/strategies/live.py](../../src/animetta/tools/minecraft/voyager/strategies/live.py)
- [src/animetta/tools/minecraft/voyager/strategies/mission.py](../../src/animetta/tools/minecraft/voyager/strategies/mission.py)

#### src/animetta/tracing

- [src/animetta/tracing/__init__.py](../../src/animetta/tracing/__init__.py)
- [src/animetta/tracing/proxy.py](../../src/animetta/tracing/proxy.py)

#### src/animetta/utils

- [src/animetta/utils/__init__.py](../../src/animetta/utils/__init__.py)
- [src/animetta/utils/auto_config.py](../../src/animetta/utils/auto_config.py)
- [src/animetta/utils/env_helper.py](../../src/animetta/utils/env_helper.py)
- [src/animetta/utils/logger_manager.py](../../src/animetta/utils/logger_manager.py)
- [src/animetta/utils/service_availability.py](../../src/animetta/utils/service_availability.py)
- [src/animetta/utils/tempfiles.py](../../src/animetta/utils/tempfiles.py)

### tests

#### tests

- [tests/__init__.py](../../tests/__init__.py)
- [tests/AGENTS.md](../../tests/AGENTS.md)
- [tests/conftest.py](../../tests/conftest.py)
- [tests/test_emotion_analyzer_fix.py](../../tests/test_emotion_analyzer_fix.py)
- [tests/test_llm_node_personality_bridge.py](../../tests/test_llm_node_personality_bridge.py)
- [tests/test_provider_availability.py](../../tests/test_provider_availability.py)

#### tests/acceptance

- [tests/acceptance/test_conversation_continuity_contract.py](../../tests/acceptance/test_conversation_continuity_contract.py)
- [tests/acceptance/test_golden_soak.py](../../tests/acceptance/test_golden_soak.py)
- [tests/acceptance/test_live_danmaku_collector.py](../../tests/acceptance/test_live_danmaku_collector.py)
- [tests/acceptance/test_livestream_conversation_continuity.py](../../tests/acceptance/test_livestream_conversation_continuity.py)
- [tests/acceptance/test_minecraft_gameplay_review.py](../../tests/acceptance/test_minecraft_gameplay_review.py)
- [tests/acceptance/test_tts_audition_clients.py](../../tests/acceptance/test_tts_audition_clients.py)
- [tests/acceptance/test_tts_audition_evidence.py](../../tests/acceptance/test_tts_audition_evidence.py)
- [tests/acceptance/test_tts_audition_plan.py](../../tests/acceptance/test_tts_audition_plan.py)
- [tests/acceptance/test_tts_audition_runner.py](../../tests/acceptance/test_tts_audition_runner.py)
- [tests/acceptance/test_tts_failover_review.py](../../tests/acceptance/test_tts_failover_review.py)

#### tests/agent_skills

- [tests/agent_skills/test_bilibili_live.py](../../tests/agent_skills/test_bilibili_live.py)
- [tests/agent_skills/test_continuity_regression_skill.py](../../tests/agent_skills/test_continuity_regression_skill.py)
- [tests/agent_skills/test_danmaku_simulator.py](../../tests/agent_skills/test_danmaku_simulator.py)
- [tests/agent_skills/test_skill_regression_scripts.py](../../tests/agent_skills/test_skill_regression_scripts.py)

#### tests/avatar

- [tests/avatar/test_audio_analyzer.py](../../tests/avatar/test_audio_analyzer.py)
- [tests/avatar/test_duration_strategy.py](../../tests/avatar/test_duration_strategy.py)
- [tests/avatar/test_emotion_param_mapper.py](../../tests/avatar/test_emotion_param_mapper.py)
- [tests/avatar/test_factory.py](../../tests/avatar/test_factory.py)
- [tests/avatar/test_intensity_strategy.py](../../tests/avatar/test_intensity_strategy.py)
- [tests/avatar/test_keyword_analyzer.py](../../tests/avatar/test_keyword_analyzer.py)
- [tests/avatar/test_llm_tag_analyzer.py](../../tests/avatar/test_llm_tag_analyzer.py)
- [tests/avatar/test_mao_performance_contract.py](../../tests/avatar/test_mao_performance_contract.py)
- [tests/avatar/test_performance_plan.py](../../tests/avatar/test_performance_plan.py)
- [tests/avatar/test_performance_prompt.py](../../tests/avatar/test_performance_prompt.py)
- [tests/avatar/test_position_strategy.py](../../tests/avatar/test_position_strategy.py)
- [tests/avatar/test_prompts.py](../../tests/avatar/test_prompts.py)

#### tests/avatar/mappers

- [tests/avatar/mappers/__init__.py](../../tests/avatar/mappers/__init__.py)
- [tests/avatar/mappers/test_base.py](../../tests/avatar/mappers/test_base.py)

#### tests/config

- [tests/config/__init__.py](../../tests/config/__init__.py)
- [tests/config/conftest.py](../../tests/config/conftest.py)
- [tests/config/test_bilibili_config.py](../../tests/config/test_bilibili_config.py)
- [tests/config/test_deepseek_config.py](../../tests/config/test_deepseek_config.py)
- [tests/config/test_import_boundaries.py](../../tests/config/test_import_boundaries.py)
- [tests/config/test_knowledge_boundaries.py](../../tests/config/test_knowledge_boundaries.py)
- [tests/config/test_live2d_config.py](../../tests/config/test_live2d_config.py)
- [tests/config/test_mbti_models.py](../../tests/config/test_mbti_models.py)
- [tests/config/test_persona.py](../../tests/config/test_persona.py)
- [tests/config/test_proactive_topics_config.py](../../tests/config/test_proactive_topics_config.py)
- [tests/config/test_provider_mixins.py](../../tests/config/test_provider_mixins.py)
- [tests/config/test_provider_registry.py](../../tests/config/test_provider_registry.py)
- [tests/config/test_registry.py](../../tests/config/test_registry.py)
- [tests/config/test_runtime_config_reloader.py](../../tests/config/test_runtime_config_reloader.py)
- [tests/config/test_runtime_manifest.py](../../tests/config/test_runtime_manifest.py)
- [tests/config/test_scene_analysis_config.py](../../tests/config/test_scene_analysis_config.py)
- [tests/config/test_security_config.py](../../tests/config/test_security_config.py)
- [tests/config/test_user_settings.py](../../tests/config/test_user_settings.py)

#### tests/config/fixtures

- [tests/config/fixtures/legacy_runtime_selectors.json](../../tests/config/fixtures/legacy_runtime_selectors.json)

#### tests/core

- [tests/core/__init__.py](../../tests/core/__init__.py)
- [tests/core/test_component_readiness.py](../../tests/core/test_component_readiness.py)
- [tests/core/test_effective_config_propagation.py](../../tests/core/test_effective_config_propagation.py)
- [tests/core/test_effective_runtime_readiness.py](../../tests/core/test_effective_runtime_readiness.py)
- [tests/core/test_golden_preflight.py](../../tests/core/test_golden_preflight.py)
- [tests/core/test_message_filter.py](../../tests/core/test_message_filter.py)
- [tests/core/test_model_loading_manager.py](../../tests/core/test_model_loading_manager.py)
- [tests/core/test_notifier.py](../../tests/core/test_notifier.py)
- [tests/core/test_redis_checkpoint.py](../../tests/core/test_redis_checkpoint.py)
- [tests/core/test_runtime_readiness.py](../../tests/core/test_runtime_readiness.py)
- [tests/core/test_service_context.py](../../tests/core/test_service_context.py)
- [tests/core/test_service_pool.py](../../tests/core/test_service_pool.py)
- [tests/core/test_shared_memory_runtime.py](../../tests/core/test_shared_memory_runtime.py)
- [tests/core/test_socketio_server.py](../../tests/core/test_socketio_server.py)

#### tests/deployment

- [tests/deployment/test_core_dependency_boundary.py](../../tests/deployment/test_core_dependency_boundary.py)
- [tests/deployment/test_legacy_runtime_gate.py](../../tests/deployment/test_legacy_runtime_gate.py)
- [tests/deployment/test_runtime_topology.py](../../tests/deployment/test_runtime_topology.py)

#### tests/eval

- [tests/eval/__init__.py](../../tests/eval/__init__.py)
- [tests/eval/anima_eval_runner.py](../../tests/eval/anima_eval_runner.py)
- [tests/eval/conftest.py](../../tests/eval/conftest.py)
- [tests/eval/test_anima_eval_scoring.py](../../tests/eval/test_anima_eval_scoring.py)
- [tests/eval/test_anima_roleplay_eval.py](../../tests/eval/test_anima_roleplay_eval.py)
- [tests/eval/test_metrics.py](../../tests/eval/test_metrics.py)
- [tests/eval/test_rag_quality.py](../../tests/eval/test_rag_quality.py)
- [tests/eval/test_rag_runner_contract.py](../../tests/eval/test_rag_runner_contract.py)

#### tests/evaluations

- [tests/evaluations/__init__.py](../../tests/evaluations/__init__.py)

#### tests/evaluations/agent

- [tests/evaluations/agent/test_agent_evaluation.py](../../tests/evaluations/agent/test_agent_evaluation.py)

#### tests/evaluations/livestream

- [tests/evaluations/livestream/__init__.py](../../tests/evaluations/livestream/__init__.py)
- [tests/evaluations/livestream/test_capture.py](../../tests/evaluations/livestream/test_capture.py)
- [tests/evaluations/livestream/test_clean_pipeline.py](../../tests/evaluations/livestream/test_clean_pipeline.py)
- [tests/evaluations/livestream/test_cleaning_evidence.py](../../tests/evaluations/livestream/test_cleaning_evidence.py)
- [tests/evaluations/livestream/test_cleaning.py](../../tests/evaluations/livestream/test_cleaning.py)
- [tests/evaluations/livestream/test_dataset_v2.py](../../tests/evaluations/livestream/test_dataset_v2.py)
- [tests/evaluations/livestream/test_dataset.py](../../tests/evaluations/livestream/test_dataset.py)
- [tests/evaluations/livestream/test_judge.py](../../tests/evaluations/livestream/test_judge.py)
- [tests/evaluations/livestream/test_livestream_eval_cli.py](../../tests/evaluations/livestream/test_livestream_eval_cli.py)
- [tests/evaluations/livestream/test_medium_derivation.py](../../tests/evaluations/livestream/test_medium_derivation.py)
- [tests/evaluations/livestream/test_reporting.py](../../tests/evaluations/livestream/test_reporting.py)
- [tests/evaluations/livestream/test_runner.py](../../tests/evaluations/livestream/test_runner.py)
- [tests/evaluations/livestream/test_scenario_enrichment.py](../../tests/evaluations/livestream/test_scenario_enrichment.py)
- [tests/evaluations/livestream/test_semantic_processor.py](../../tests/evaluations/livestream/test_semantic_processor.py)
- [tests/evaluations/livestream/test_socket_processor.py](../../tests/evaluations/livestream/test_socket_processor.py)
- [tests/evaluations/livestream/test_twitch_vod_capture.py](../../tests/evaluations/livestream/test_twitch_vod_capture.py)

#### tests/fixtures

- [tests/fixtures/gamebot_contract_v1.json](../../tests/fixtures/gamebot_contract_v1.json)

#### tests/fixtures/audio

- [tests/fixtures/audio/singing_test.m4a](../../tests/fixtures/audio/singing_test.m4a)

#### tests/fixtures/bilibili

- [tests/fixtures/bilibili/protocol_events.json](../../tests/fixtures/bilibili/protocol_events.json)

#### tests/inspection

- [tests/inspection/__init__.py](../../tests/inspection/__init__.py)
- [tests/inspection/test_consistency.py](../../tests/inspection/test_consistency.py)
- [tests/inspection/test_health.py](../../tests/inspection/test_health.py)
- [tests/inspection/test_metrics.py](../../tests/inspection/test_metrics.py)
- [tests/inspection/test_models.py](../../tests/inspection/test_models.py)
- [tests/inspection/test_observed_turn.py](../../tests/inspection/test_observed_turn.py)
- [tests/inspection/test_pipeline.py](../../tests/inspection/test_pipeline.py)
- [tests/inspection/test_runtime_health.py](../../tests/inspection/test_runtime_health.py)
- [tests/inspection/test_scheduler.py](../../tests/inspection/test_scheduler.py)

#### tests/integration

- [tests/integration/__init__.py](../../tests/integration/__init__.py)
- [tests/integration/conftest.py](../../tests/integration/conftest.py)
- [tests/integration/test_asr_pipeline.py](../../tests/integration/test_asr_pipeline.py)
- [tests/integration/test_conversation_flow.py](../../tests/integration/test_conversation_flow.py)
- [tests/integration/test_emotion_pipeline.py](../../tests/integration/test_emotion_pipeline.py)
- [tests/integration/test_golden_socket_contract.py](../../tests/integration/test_golden_socket_contract.py)
- [tests/integration/test_health.py](../../tests/integration/test_health.py)
- [tests/integration/test_live2d_pipeline.py](../../tests/integration/test_live2d_pipeline.py)
- [tests/integration/test_memory.py](../../tests/integration/test_memory.py)
- [tests/integration/test_minecraft.py](../../tests/integration/test_minecraft.py)
- [tests/integration/test_tool_calling.py](../../tests/integration/test_tool_calling.py)
- [tests/integration/test_translation.py](../../tests/integration/test_translation.py)

#### tests/mcp/bilibili

- [tests/mcp/bilibili/__init__.py](../../tests/mcp/bilibili/__init__.py)
- [tests/mcp/bilibili/test_controller.py](../../tests/mcp/bilibili/test_controller.py)
- [tests/mcp/bilibili/test_server.py](../../tests/mcp/bilibili/test_server.py)

#### tests/memory_v2

- [tests/memory_v2/test_atom.py](../../tests/memory_v2/test_atom.py)
- [tests/memory_v2/test_character_filter.py](../../tests/memory_v2/test_character_filter.py)
- [tests/memory_v2/test_compile.py](../../tests/memory_v2/test_compile.py)
- [tests/memory_v2/test_contract.py](../../tests/memory_v2/test_contract.py)
- [tests/memory_v2/test_emotion_field.py](../../tests/memory_v2/test_emotion_field.py)
- [tests/memory_v2/test_metabolism_integration.py](../../tests/memory_v2/test_metabolism_integration.py)
- [tests/memory_v2/test_metabolism.py](../../tests/memory_v2/test_metabolism.py)
- [tests/memory_v2/test_reconsolidation.py](../../tests/memory_v2/test_reconsolidation.py)
- [tests/memory_v2/test_scoped_recall.py](../../tests/memory_v2/test_scoped_recall.py)
- [tests/memory_v2/test_search.py](../../tests/memory_v2/test_search.py)
- [tests/memory_v2/test_seed_generator.py](../../tests/memory_v2/test_seed_generator.py)
- [tests/memory_v2/test_shared_schema.py](../../tests/memory_v2/test_shared_schema.py)
- [tests/memory_v2/test_store_async.py](../../tests/memory_v2/test_store_async.py)
- [tests/memory_v2/test_store.py](../../tests/memory_v2/test_store.py)
- [tests/memory_v2/test_system.py](../../tests/memory_v2/test_system.py)

#### tests/observability

- [tests/observability/test_application_lifecycle.py](../../tests/observability/test_application_lifecycle.py)
- [tests/observability/test_architecture.py](../../tests/observability/test_architecture.py)
- [tests/observability/test_chat_delivery_observation.py](../../tests/observability/test_chat_delivery_observation.py)
- [tests/observability/test_conversation_observer.py](../../tests/observability/test_conversation_observer.py)
- [tests/observability/test_domain.py](../../tests/observability/test_domain.py)
- [tests/observability/test_errors.py](../../tests/observability/test_errors.py)
- [tests/observability/test_graph_instrumentation.py](../../tests/observability/test_graph_instrumentation.py)
- [tests/observability/test_ledger_lifecycle.py](../../tests/observability/test_ledger_lifecycle.py)
- [tests/observability/test_ledger_query.py](../../tests/observability/test_ledger_query.py)
- [tests/observability/test_ledger_queue.py](../../tests/observability/test_ledger_queue.py)
- [tests/observability/test_ledger_schema.py](../../tests/observability/test_ledger_schema.py)
- [tests/observability/test_legacy_removal.py](../../tests/observability/test_legacy_removal.py)
- [tests/observability/test_memory_observation.py](../../tests/observability/test_memory_observation.py)
- [tests/observability/test_otel_mirror.py](../../tests/observability/test_otel_mirror.py)
- [tests/observability/test_ports.py](../../tests/observability/test_ports.py)
- [tests/observability/test_privacy.py](../../tests/observability/test_privacy.py)
- [tests/observability/test_prometheus_mirror.py](../../tests/observability/test_prometheus_mirror.py)
- [tests/observability/test_query_api.py](../../tests/observability/test_query_api.py)
- [tests/observability/test_real_graph_topology.py](../../tests/observability/test_real_graph_topology.py)
- [tests/observability/test_reset_command.py](../../tests/observability/test_reset_command.py)
- [tests/observability/test_service_factory_instrumentation.py](../../tests/observability/test_service_factory_instrumentation.py)
- [tests/observability/test_service_proxy.py](../../tests/observability/test_service_proxy.py)
- [tests/observability/test_tool_invocation_observer.py](../../tests/observability/test_tool_invocation_observer.py)

#### tests/orchestration

- [tests/orchestration/test_bilibili_event_contract.py](../../tests/orchestration/test_bilibili_event_contract.py)
- [tests/orchestration/test_chat_contracts.py](../../tests/orchestration/test_chat_contracts.py)
- [tests/orchestration/test_chat_delivery.py](../../tests/orchestration/test_chat_delivery.py)
- [tests/orchestration/test_socket_event_contract.py](../../tests/orchestration/test_socket_event_contract.py)
- [tests/orchestration/test_socket_events.py](../../tests/orchestration/test_socket_events.py)

#### tests/orchestration/graph

- [tests/orchestration/graph/test_anima_v01_regression.py](../../tests/orchestration/graph/test_anima_v01_regression.py)
- [tests/orchestration/graph/test_asr_node.py](../../tests/orchestration/graph/test_asr_node.py)
- [tests/orchestration/graph/test_builder.py](../../tests/orchestration/graph/test_builder.py)
- [tests/orchestration/graph/test_conversation_session_state.py](../../tests/orchestration/graph/test_conversation_session_state.py)
- [tests/orchestration/graph/test_developer_live_prompt.py](../../tests/orchestration/graph/test_developer_live_prompt.py)
- [tests/orchestration/graph/test_dialogue_nodes.py](../../tests/orchestration/graph/test_dialogue_nodes.py)
- [tests/orchestration/graph/test_emotion_node.py](../../tests/orchestration/graph/test_emotion_node.py)
- [tests/orchestration/graph/test_golden_delivery_nodes.py](../../tests/orchestration/graph/test_golden_delivery_nodes.py)
- [tests/orchestration/graph/test_humor_nodes.py](../../tests/orchestration/graph/test_humor_nodes.py)
- [tests/orchestration/graph/test_identity_propagation.py](../../tests/orchestration/graph/test_identity_propagation.py)
- [tests/orchestration/graph/test_interrupt_handler.py](../../tests/orchestration/graph/test_interrupt_handler.py)
- [tests/orchestration/graph/test_llm_node_context_budget.py](../../tests/orchestration/graph/test_llm_node_context_budget.py)
- [tests/orchestration/graph/test_llm_node.py](../../tests/orchestration/graph/test_llm_node.py)
- [tests/orchestration/graph/test_memory_middleware.py](../../tests/orchestration/graph/test_memory_middleware.py)
- [tests/orchestration/graph/test_memory_pressure.py](../../tests/orchestration/graph/test_memory_pressure.py)
- [tests/orchestration/graph/test_minecraft_mission_dialogue.py](../../tests/orchestration/graph/test_minecraft_mission_dialogue.py)
- [tests/orchestration/graph/test_node_error.py](../../tests/orchestration/graph/test_node_error.py)
- [tests/orchestration/graph/test_observability.py](../../tests/orchestration/graph/test_observability.py)
- [tests/orchestration/graph/test_orchestrator_config_version.py](../../tests/orchestration/graph/test_orchestrator_config_version.py)
- [tests/orchestration/graph/test_orchestrator.py](../../tests/orchestration/graph/test_orchestrator.py)
- [tests/orchestration/graph/test_output_node.py](../../tests/orchestration/graph/test_output_node.py)
- [tests/orchestration/graph/test_persistence_policy.py](../../tests/orchestration/graph/test_persistence_policy.py)
- [tests/orchestration/graph/test_personality_node.py](../../tests/orchestration/graph/test_personality_node.py)
- [tests/orchestration/graph/test_prompt_assembler.py](../../tests/orchestration/graph/test_prompt_assembler.py)
- [tests/orchestration/graph/test_prompt_pipeline.py](../../tests/orchestration/graph/test_prompt_pipeline.py)
- [tests/orchestration/graph/test_roleplay_guard.py](../../tests/orchestration/graph/test_roleplay_guard.py)
- [tests/orchestration/graph/test_scheduler.py](../../tests/orchestration/graph/test_scheduler.py)
- [tests/orchestration/graph/test_state.py](../../tests/orchestration/graph/test_state.py)
- [tests/orchestration/graph/test_subtitle_translator.py](../../tests/orchestration/graph/test_subtitle_translator.py)
- [tests/orchestration/graph/test_tool_approval.py](../../tests/orchestration/graph/test_tool_approval.py)
- [tests/orchestration/graph/test_tool_execution_policy.py](../../tests/orchestration/graph/test_tool_execution_policy.py)
- [tests/orchestration/graph/test_tool_manager.py](../../tests/orchestration/graph/test_tool_manager.py)
- [tests/orchestration/graph/test_tool_node.py](../../tests/orchestration/graph/test_tool_node.py)
- [tests/orchestration/graph/test_translation_state.py](../../tests/orchestration/graph/test_translation_state.py)
- [tests/orchestration/graph/test_tts_node.py](../../tests/orchestration/graph/test_tts_node.py)

#### tests/orchestration/server

- [tests/orchestration/server/__init__.py](../../tests/orchestration/server/__init__.py)
- [tests/orchestration/server/test_auth_session.py](../../tests/orchestration/server/test_auth_session.py)
- [tests/orchestration/server/test_auth_user.py](../../tests/orchestration/server/test_auth_user.py)
- [tests/orchestration/server/test_bilibili_handlers.py](../../tests/orchestration/server/test_bilibili_handlers.py)
- [tests/orchestration/server/test_chat_handler_contract.py](../../tests/orchestration/server/test_chat_handler_contract.py)
- [tests/orchestration/server/test_config_reload_api.py](../../tests/orchestration/server/test_config_reload_api.py)
- [tests/orchestration/server/test_desktop.py](../../tests/orchestration/server/test_desktop.py)
- [tests/orchestration/server/test_earth_handlers.py](../../tests/orchestration/server/test_earth_handlers.py)
- [tests/orchestration/server/test_frontend_health.py](../../tests/orchestration/server/test_frontend_health.py)
- [tests/orchestration/server/test_lifecycle.py](../../tests/orchestration/server/test_lifecycle.py)
- [tests/orchestration/server/test_live2d_server.py](../../tests/orchestration/server/test_live2d_server.py)
- [tests/orchestration/server/test_live2d.py](../../tests/orchestration/server/test_live2d.py)
- [tests/orchestration/server/test_memory_contract.py](../../tests/orchestration/server/test_memory_contract.py)
- [tests/orchestration/server/test_persona_config_immutability.py](../../tests/orchestration/server/test_persona_config_immutability.py)
- [tests/orchestration/server/test_program_script_api.py](../../tests/orchestration/server/test_program_script_api.py)
- [tests/orchestration/server/test_routes.py](../../tests/orchestration/server/test_routes.py)
- [tests/orchestration/server/test_security.py](../../tests/orchestration/server/test_security.py)
- [tests/orchestration/server/test_session.py](../../tests/orchestration/server/test_session.py)
- [tests/orchestration/server/test_singing_handlers.py](../../tests/orchestration/server/test_singing_handlers.py)
- [tests/orchestration/server/test_stats_api.py](../../tests/orchestration/server/test_stats_api.py)
- [tests/orchestration/server/test_tool_approval_routes.py](../../tests/orchestration/server/test_tool_approval_routes.py)
- [tests/orchestration/server/test_websocket.py](../../tests/orchestration/server/test_websocket.py)

#### tests/orchestration/server/handlers

- [tests/orchestration/server/handlers/test_live2d_handlers.py](../../tests/orchestration/server/handlers/test_live2d_handlers.py)
- [tests/orchestration/server/handlers/test_minecraft_activity_wiring.py](../../tests/orchestration/server/handlers/test_minecraft_activity_wiring.py)
- [tests/orchestration/server/handlers/test_minecraft_viewer_status.py](../../tests/orchestration/server/handlers/test_minecraft_viewer_status.py)
- [tests/orchestration/server/handlers/test_minecraft_voyager_wiring.py](../../tests/orchestration/server/handlers/test_minecraft_voyager_wiring.py)

#### tests/persona_lab

- [tests/persona_lab/test_training_lab_runtime_boundary.py](../../tests/persona_lab/test_training_lab_runtime_boundary.py)

#### tests/scripts

- [tests/scripts/test_baseline_golden_path.py](../../tests/scripts/test_baseline_golden_path.py)
- [tests/scripts/test_benchmark_host_tts.py](../../tests/scripts/test_benchmark_host_tts.py)
- [tests/scripts/test_benchmark_startup.py](../../tests/scripts/test_benchmark_startup.py)
- [tests/scripts/test_benchmark_storage.py](../../tests/scripts/test_benchmark_storage.py)
- [tests/scripts/test_conversation_continuity_canary.py](../../tests/scripts/test_conversation_continuity_canary.py)
- [tests/scripts/test_manage_users.py](../../tests/scripts/test_manage_users.py)
- [tests/scripts/test_probe_release_turn.py](../../tests/scripts/test_probe_release_turn.py)
- [tests/scripts/test_python_lock.py](../../tests/scripts/test_python_lock.py)
- [tests/scripts/test_qwen_preflight.py](../../tests/scripts/test_qwen_preflight.py)
- [tests/scripts/test_release_runtime_gate.py](../../tests/scripts/test_release_runtime_gate.py)
- [tests/scripts/test_runtime_lifecycle_feedback.py](../../tests/scripts/test_runtime_lifecycle_feedback.py)
- [tests/scripts/test_runtime_lifecycle.py](../../tests/scripts/test_runtime_lifecycle.py)
- [tests/scripts/test_rvc_preflight.py](../../tests/scripts/test_rvc_preflight.py)
- [tests/scripts/test_smoke_real_profile.py](../../tests/scripts/test_smoke_real_profile.py)
- [tests/scripts/test_startup_cache.py](../../tests/scripts/test_startup_cache.py)

#### tests/scripts/train

- [tests/scripts/train/test_prepare_data.py](../../tests/scripts/train/test_prepare_data.py)
- [tests/scripts/train/test_prepare_rvc_experiment.py](../../tests/scripts/train/test_prepare_rvc_experiment.py)
- [tests/scripts/train/test_review_data.py](../../tests/scripts/train/test_review_data.py) — 未提交
- [tests/scripts/train/test_training_runner.py](../../tests/scripts/train/test_training_runner.py)
- [tests/scripts/train/test_workspace.py](../../tests/scripts/train/test_workspace.py)

#### tests/services

- [tests/services/__init__.py](../../tests/services/__init__.py)
- [tests/services/test_asr_providers.py](../../tests/services/test_asr_providers.py)
- [tests/services/test_bilibili_danmaku.py](../../tests/services/test_bilibili_danmaku.py)
- [tests/services/test_command_inbox.py](../../tests/services/test_command_inbox.py)
- [tests/services/test_glm_message_converter.py](../../tests/services/test_glm_message_converter.py)
- [tests/services/test_langchain_adapter.py](../../tests/services/test_langchain_adapter.py)
- [tests/services/test_live2d_action_queue.py](../../tests/services/test_live2d_action_queue.py)
- [tests/services/test_live2d_preset_loader.py](../../tests/services/test_live2d_preset_loader.py)
- [tests/services/test_live2d_viseme_sync.py](../../tests/services/test_live2d_viseme_sync.py)
- [tests/services/test_livestream_narration.py](../../tests/services/test_livestream_narration.py)
- [tests/services/test_llm_factory.py](../../tests/services/test_llm_factory.py)
- [tests/services/test_llm_providers.py](../../tests/services/test_llm_providers.py)
- [tests/services/test_tts_providers.py](../../tests/services/test_tts_providers.py)
- [tests/services/test_vad_providers.py](../../tests/services/test_vad_providers.py)

#### tests/services/asr

- [tests/services/asr/__init__.py](../../tests/services/asr/__init__.py)
- [tests/services/asr/test_asr_factory.py](../../tests/services/asr/test_asr_factory.py)
- [tests/services/asr/test_mimo_asr.py](../../tests/services/asr/test_mimo_asr.py)

#### tests/services/audio

- [tests/services/audio/__init__.py](../../tests/services/audio/__init__.py)
- [tests/services/audio/test_processor.py](../../tests/services/audio/test_processor.py)
- [tests/services/audio/test_simple_vad_processor.py](../../tests/services/audio/test_simple_vad_processor.py)
- [tests/services/audio/test_vad_processor.py](../../tests/services/audio/test_vad_processor.py)

#### tests/services/bilibili

- [tests/services/bilibili/__init__.py](../../tests/services/bilibili/__init__.py)
- [tests/services/bilibili/test_api.py](../../tests/services/bilibili/test_api.py)
- [tests/services/bilibili/test_bilibili_models.py](../../tests/services/bilibili/test_bilibili_models.py)
- [tests/services/bilibili/test_broadcast_media.py](../../tests/services/bilibili/test_broadcast_media.py)
- [tests/services/bilibili/test_danmaku_service.py](../../tests/services/bilibili/test_danmaku_service.py)
- [tests/services/bilibili/test_event_normalizer.py](../../tests/services/bilibili/test_event_normalizer.py)
- [tests/services/bilibili/test_livestream_session.py](../../tests/services/bilibili/test_livestream_session.py)
- [tests/services/bilibili/test_proactive_topics.py](../../tests/services/bilibili/test_proactive_topics.py)
- [tests/services/bilibili/test_replay_gateway.py](../../tests/services/bilibili/test_replay_gateway.py)
- [tests/services/bilibili/test_replay_session_integration.py](../../tests/services/bilibili/test_replay_session_integration.py)
- [tests/services/bilibili/test_reply_admission.py](../../tests/services/bilibili/test_reply_admission.py)
- [tests/services/bilibili/test_reply_queue.py](../../tests/services/bilibili/test_reply_queue.py)
- [tests/services/bilibili/test_response_policy.py](../../tests/services/bilibili/test_response_policy.py)

#### tests/services/dialogue

- [tests/services/dialogue/test_contracts.py](../../tests/services/dialogue/test_contracts.py)
- [tests/services/dialogue/test_sandbox.py](../../tests/services/dialogue/test_sandbox.py)
- [tests/services/dialogue/test_services.py](../../tests/services/dialogue/test_services.py)

#### tests/services/earth

- [tests/services/earth/test_audio.py](../../tests/services/earth/test_audio.py)
- [tests/services/earth/test_exploration.py](../../tests/services/earth/test_exploration.py)

#### tests/services/effects

- [tests/services/effects/test_effect_runtime.py](../../tests/services/effects/test_effect_runtime.py)

#### tests/services/humor

- [tests/services/humor/test_humor_agent.py](../../tests/services/humor/test_humor_agent.py)

#### tests/services/live2d

- [tests/services/live2d/test_viseme_sync.py](../../tests/services/live2d/test_viseme_sync.py)

#### tests/services/llm

- [tests/services/llm/__init__.py](../../tests/services/llm/__init__.py)
- [tests/services/llm/test_deepseek_policy.py](../../tests/services/llm/test_deepseek_policy.py)
- [tests/services/llm/test_explicit_history_contract.py](../../tests/services/llm/test_explicit_history_contract.py)
- [tests/services/llm/test_history_trimming.py](../../tests/services/llm/test_history_trimming.py)
- [tests/services/llm/test_stream_handler.py](../../tests/services/llm/test_stream_handler.py)
- [tests/services/llm/test_tool_handler.py](../../tests/services/llm/test_tool_handler.py)
- [tests/services/llm/test_usage.py](../../tests/services/llm/test_usage.py)

#### tests/services/meme

- [tests/services/meme/__init__.py](../../tests/services/meme/__init__.py)
- [tests/services/meme/test_analyzer.py](../../tests/services/meme/test_analyzer.py)
- [tests/services/meme/test_bilibili_collector.py](../../tests/services/meme/test_bilibili_collector.py)
- [tests/services/meme/test_bilibili_interaction.py](../../tests/services/meme/test_bilibili_interaction.py)
- [tests/services/meme/test_danmaku_buffer.py](../../tests/services/meme/test_danmaku_buffer.py)
- [tests/services/meme/test_danmaku_collector_integration.py](../../tests/services/meme/test_danmaku_collector_integration.py)
- [tests/services/meme/test_heuristic_semantic.py](../../tests/services/meme/test_heuristic_semantic.py)
- [tests/services/meme/test_style_tools.py](../../tests/services/meme/test_style_tools.py)

#### tests/services/program_script

- [tests/services/program_script/__init__.py](../../tests/services/program_script/__init__.py)
- [tests/services/program_script/test_models.py](../../tests/services/program_script/test_models.py)
- [tests/services/program_script/test_replay.py](../../tests/services/program_script/test_replay.py)
- [tests/services/program_script/test_repository.py](../../tests/services/program_script/test_repository.py)
- [tests/services/program_script/test_runtime.py](../../tests/services/program_script/test_runtime.py)

#### tests/services/scene_analysis

- [tests/services/scene_analysis/test_model_gateway.py](../../tests/services/scene_analysis/test_model_gateway.py)
- [tests/services/scene_analysis/test_replay.py](../../tests/services/scene_analysis/test_replay.py)
- [tests/services/scene_analysis/test_runtime.py](../../tests/services/scene_analysis/test_runtime.py)
- [tests/services/scene_analysis/test_scene_contracts.py](../../tests/services/scene_analysis/test_scene_contracts.py)

#### tests/services/separation

- [tests/services/separation/__init__.py](../../tests/services/separation/__init__.py)
- [tests/services/separation/test_separation_factory.py](../../tests/services/separation/test_separation_factory.py)

#### tests/services/singing

- [tests/services/singing/__init__.py](../../tests/services/singing/__init__.py)
- [tests/services/singing/test_bilibili.py](../../tests/services/singing/test_bilibili.py)
- [tests/services/singing/test_mixer.py](../../tests/services/singing/test_mixer.py)
- [tests/services/singing/test_rvc_bridge.py](../../tests/services/singing/test_rvc_bridge.py)
- [tests/services/singing/test_rvc_host_app.py](../../tests/services/singing/test_rvc_host_app.py)
- [tests/services/singing/test_rvc_host_engine.py](../../tests/services/singing/test_rvc_host_engine.py)
- [tests/services/singing/test_separator.py](../../tests/services/singing/test_separator.py)
- [tests/services/singing/test_singing_interface.py](../../tests/services/singing/test_singing_interface.py)
- [tests/services/singing/test_svc_pipeline_rvc.py](../../tests/services/singing/test_svc_pipeline_rvc.py)

#### tests/services/tts

- [tests/services/tts/__init__.py](../../tests/services/tts/__init__.py)
- [tests/services/tts/test_dashscope_realtime_tts.py](../../tests/services/tts/test_dashscope_realtime_tts.py)
- [tests/services/tts/test_failover_tts.py](../../tests/services/tts/test_failover_tts.py)
- [tests/services/tts/test_mimo_tts.py](../../tests/services/tts/test_mimo_tts.py)
- [tests/services/tts/test_mock_tts_identity.py](../../tests/services/tts/test_mock_tts_identity.py)
- [tests/services/tts/test_qwen_gguf_host_engine.py](../../tests/services/tts/test_qwen_gguf_host_engine.py)
- [tests/services/tts/test_qwen_tts_service_contract.py](../../tests/services/tts/test_qwen_tts_service_contract.py)
- [tests/services/tts/test_qwen3_concurrency.py](../../tests/services/tts/test_qwen3_concurrency.py)
- [tests/services/tts/test_qwen3_hf_isolation.py](../../tests/services/tts/test_qwen3_hf_isolation.py)
- [tests/services/tts/test_remote_tts_contract.py](../../tests/services/tts/test_remote_tts_contract.py)
- [tests/services/tts/test_streaming.py](../../tests/services/tts/test_streaming.py)
- [tests/services/tts/test_tts_factory.py](../../tests/services/tts/test_tts_factory.py)

#### tests/services/vad

- [tests/services/vad/__init__.py](../../tests/services/vad/__init__.py)
- [tests/services/vad/test_mimo_vad.py](../../tests/services/vad/test_mimo_vad.py)
- [tests/services/vad/test_vad_factory.py](../../tests/services/vad/test_vad_factory.py)

#### tests/services/vc

- [tests/services/vc/__init__.py](../../tests/services/vc/__init__.py)
- [tests/services/vc/test_vc_factory.py](../../tests/services/vc/test_vc_factory.py)

#### tests/smoke

- [tests/smoke/__init__.py](../../tests/smoke/__init__.py)
- [tests/smoke/conversation_e2e.py](../../tests/smoke/conversation_e2e.py)
- [tests/smoke/test_check_secrets.py](../../tests/smoke/test_check_secrets.py)
- [tests/smoke/test_docker_frontend.py](../../tests/smoke/test_docker_frontend.py)
- [tests/smoke/test_frontend_agents_docs.py](../../tests/smoke/test_frontend_agents_docs.py)
- [tests/smoke/test_health_check.py](../../tests/smoke/test_health_check.py)
- [tests/smoke/test_main_path.py](../../tests/smoke/test_main_path.py)
- [tests/smoke/test_meme_collector.py](../../tests/smoke/test_meme_collector.py)
- [tests/smoke/test_python_runtime_policy.py](../../tests/smoke/test_python_runtime_policy.py)
- [tests/smoke/test_readme_alignment.py](../../tests/smoke/test_readme_alignment.py)
- [tests/smoke/test_route_smoke.py](../../tests/smoke/test_route_smoke.py)
- [tests/smoke/test_singing_pipeline.py](../../tests/smoke/test_singing_pipeline.py)
- [tests/smoke/test_source_hygiene.py](../../tests/smoke/test_source_hygiene.py)
- [tests/smoke/test_validate_events.py](../../tests/smoke/test_validate_events.py)

#### tests/tooling/execution_feedback

- [tests/tooling/execution_feedback/test_core.py](../../tests/tooling/execution_feedback/test_core.py)
- [tests/tooling/execution_feedback/test_execution_feedback_cli.py](../../tests/tooling/execution_feedback/test_execution_feedback_cli.py)
- [tests/tooling/execution_feedback/test_minecraft_adapter.py](../../tests/tooling/execution_feedback/test_minecraft_adapter.py)
- [tests/tooling/execution_feedback/test_plan_and_failures.py](../../tests/tooling/execution_feedback/test_plan_and_failures.py)
- [tests/tooling/execution_feedback/test_recovery_and_leases.py](../../tests/tooling/execution_feedback/test_recovery_and_leases.py)

#### tests/tooling/quality

- [tests/tooling/quality/test_architecture_boundaries.py](../../tests/tooling/quality/test_architecture_boundaries.py)
- [tests/tooling/quality/test_cache.py](../../tests/tooling/quality/test_cache.py)
- [tests/tooling/quality/test_change_sources.py](../../tests/tooling/quality/test_change_sources.py)
- [tests/tooling/quality/test_cli.py](../../tests/tooling/quality/test_cli.py)
- [tests/tooling/quality/test_docker_plan.py](../../tests/tooling/quality/test_docker_plan.py)
- [tests/tooling/quality/test_executor.py](../../tests/tooling/quality/test_executor.py)
- [tests/tooling/quality/test_feedback_sharding.py](../../tests/tooling/quality/test_feedback_sharding.py)
- [tests/tooling/quality/test_fingerprint.py](../../tests/tooling/quality/test_fingerprint.py)
- [tests/tooling/quality/test_manifest.py](../../tests/tooling/quality/test_manifest.py)
- [tests/tooling/quality/test_minecraft_architecture.py](../../tests/tooling/quality/test_minecraft_architecture.py)
- [tests/tooling/quality/test_npm_runner.py](../../tests/tooling/quality/test_npm_runner.py)
- [tests/tooling/quality/test_path_matching.py](../../tests/tooling/quality/test_path_matching.py)
- [tests/tooling/quality/test_quality_planner.py](../../tests/tooling/quality/test_quality_planner.py)
- [tests/tooling/quality/test_quality_scheduler.py](../../tests/tooling/quality/test_quality_scheduler.py)
- [tests/tooling/quality/test_repository_style_contract.py](../../tests/tooling/quality/test_repository_style_contract.py)
- [tests/tooling/quality/test_source_standards.py](../../tests/tooling/quality/test_source_standards.py)
- [tests/tooling/quality/test_warm_topology.py](../../tests/tooling/quality/test_warm_topology.py)
- [tests/tooling/quality/test_workflow_contract.py](../../tests/tooling/quality/test_workflow_contract.py)

#### tests/tools

- [tests/tools/__init__.py](../../tests/tools/__init__.py)
- [tests/tools/test_base.py](../../tests/tools/test_base.py)
- [tests/tools/test_custom_tools.py](../../tests/tools/test_custom_tools.py)
- [tests/tools/test_earth.py](../../tests/tools/test_earth.py)
- [tests/tools/test_langchain_tools.py](../../tests/tools/test_langchain_tools.py)
- [tests/tools/test_mcp_bridge.py](../../tests/tools/test_mcp_bridge.py)

#### tests/tools/gamebot

- [tests/tools/gamebot/test_client.py](../../tests/tools/gamebot/test_client.py)
- [tests/tools/gamebot/test_command_contract.py](../../tests/tools/gamebot/test_command_contract.py)
- [tests/tools/gamebot/test_contract_fixture_parity.py](../../tests/tools/gamebot/test_contract_fixture_parity.py)
- [tests/tools/gamebot/test_error_contract.py](../../tests/tools/gamebot/test_error_contract.py)
- [tests/tools/gamebot/test_event_contract.py](../../tests/tools/gamebot/test_event_contract.py)
- [tests/tools/gamebot/test_state_collector.py](../../tests/tools/gamebot/test_state_collector.py)
- [tests/tools/gamebot/test_status_contract.py](../../tests/tools/gamebot/test_status_contract.py)
- [tests/tools/gamebot/test_stdio_transport.py](../../tests/tools/gamebot/test_stdio_transport.py)
- [tests/tools/gamebot/test_tool_adapter.py](../../tests/tools/gamebot/test_tool_adapter.py)
- [tests/tools/gamebot/test_transport_protocol.py](../../tests/tools/gamebot/test_transport_protocol.py)
- [tests/tools/gamebot/test_voyager_contract.py](../../tests/tools/gamebot/test_voyager_contract.py)

#### tests/tools/gamebot/contracts/v2

- [tests/tools/gamebot/contracts/v2/test_adaptive_evidence_models.py](../../tests/tools/gamebot/contracts/v2/test_adaptive_evidence_models.py)
- [tests/tools/gamebot/contracts/v2/test_models.py](../../tests/tools/gamebot/contracts/v2/test_models.py)
- [tests/tools/gamebot/contracts/v2/test_schema_bundle.py](../../tests/tools/gamebot/contracts/v2/test_schema_bundle.py)

#### tests/tools/minecraft

- [tests/tools/minecraft/__init__.py](../../tests/tools/minecraft/__init__.py)
- [tests/tools/minecraft/conftest.py](../../tests/tools/minecraft/conftest.py)
- [tests/tools/minecraft/SMOKE_TESTS_resource_locator.md](../../tests/tools/minecraft/SMOKE_TESTS_resource_locator.md)
- [tests/tools/minecraft/test_control_plane_characterization.py](../../tests/tools/minecraft/test_control_plane_characterization.py)
- [tests/tools/minecraft/test_migration_verification.py](../../tests/tools/minecraft/test_migration_verification.py)
- [tests/tools/minecraft/test_spectator.py](../../tests/tools/minecraft/test_spectator.py)
- [tests/tools/minecraft/test_voyager_benchmark.py](../../tests/tools/minecraft/test_voyager_benchmark.py)
- [tests/tools/minecraft/test_voyager_bridge_wiring.py](../../tests/tools/minecraft/test_voyager_bridge_wiring.py)

#### tests/tools/minecraft/benchmark

- [tests/tools/minecraft/benchmark/__init__.py](../../tests/tools/minecraft/benchmark/__init__.py)

#### tests/tools/minecraft/blueprint

- [tests/tools/minecraft/blueprint/__init__.py](../../tests/tools/minecraft/blueprint/__init__.py)
- [tests/tools/minecraft/blueprint/test_blueprint.py](../../tests/tools/minecraft/blueprint/test_blueprint.py)

#### tests/tools/minecraft/core

- [tests/tools/minecraft/core/__init__.py](../../tests/tools/minecraft/core/__init__.py)
- [tests/tools/minecraft/core/test_bridge.py](../../tests/tools/minecraft/core/test_bridge.py)
- [tests/tools/minecraft/core/test_client_viewer_bridge.py](../../tests/tools/minecraft/core/test_client_viewer_bridge.py)
- [tests/tools/minecraft/core/test_client_viewer_config.py](../../tests/tools/minecraft/core/test_client_viewer_config.py)
- [tests/tools/minecraft/core/test_config.py](../../tests/tools/minecraft/core/test_config.py)
- [tests/tools/minecraft/core/test_control_plane_assembly.py](../../tests/tools/minecraft/core/test_control_plane_assembly.py)
- [tests/tools/minecraft/core/test_gamebot_v2_adapter.py](../../tests/tools/minecraft/core/test_gamebot_v2_adapter.py)
- [tests/tools/minecraft/core/test_planner.py](../../tests/tools/minecraft/core/test_planner.py)
- [tests/tools/minecraft/core/test_public_gateway_tools.py](../../tests/tools/minecraft/core/test_public_gateway_tools.py)
- [tests/tools/minecraft/core/test_rules_engine.py](../../tests/tools/minecraft/core/test_rules_engine.py)
- [tests/tools/minecraft/core/test_trace_recorder.py](../../tests/tools/minecraft/core/test_trace_recorder.py)
- [tests/tools/minecraft/core/test_world_state.py](../../tests/tools/minecraft/core/test_world_state.py)

#### tests/tools/minecraft/demo

- [tests/tools/minecraft/demo/test_scenario.py](../../tests/tools/minecraft/demo/test_scenario.py)

#### tests/tools/minecraft/discovery

- [tests/tools/minecraft/discovery/__init__.py](../../tests/tools/minecraft/discovery/__init__.py)
- [tests/tools/minecraft/discovery/test_evidence_policy.py](../../tests/tools/minecraft/discovery/test_evidence_policy.py)
- [tests/tools/minecraft/discovery/test_exploration_proposer.py](../../tests/tools/minecraft/discovery/test_exploration_proposer.py)
- [tests/tools/minecraft/discovery/test_runtime_projection.py](../../tests/tools/minecraft/discovery/test_runtime_projection.py)
- [tests/tools/minecraft/discovery/test_world_facts.py](../../tests/tools/minecraft/discovery/test_world_facts.py)

#### tests/tools/minecraft/fixtures

- [tests/tools/minecraft/fixtures/gamebot_v1_characterization.json](../../tests/tools/minecraft/fixtures/gamebot_v1_characterization.json)

#### tests/tools/minecraft/mission

- [tests/tools/minecraft/mission/__init__.py](../../tests/tools/minecraft/mission/__init__.py)
- [tests/tools/minecraft/mission/test_adaptive_coordination.py](../../tests/tools/minecraft/mission/test_adaptive_coordination.py)
- [tests/tools/minecraft/mission/test_adaptive_policy.py](../../tests/tools/minecraft/mission/test_adaptive_policy.py)
- [tests/tools/minecraft/mission/test_adaptive_runtime.py](../../tests/tools/minecraft/mission/test_adaptive_runtime.py)
- [tests/tools/minecraft/mission/test_admission.py](../../tests/tools/minecraft/mission/test_admission.py)
- [tests/tools/minecraft/mission/test_coordinator_safety.py](../../tests/tools/minecraft/mission/test_coordinator_safety.py)
- [tests/tools/minecraft/mission/test_coordinator.py](../../tests/tools/minecraft/mission/test_coordinator.py)
- [tests/tools/minecraft/mission/test_models.py](../../tests/tools/minecraft/mission/test_models.py)
- [tests/tools/minecraft/mission/test_projection_events.py](../../tests/tools/minecraft/mission/test_projection_events.py)
- [tests/tools/minecraft/mission/test_projection.py](../../tests/tools/minecraft/mission/test_projection.py)
- [tests/tools/minecraft/mission/test_repository.py](../../tests/tools/minecraft/mission/test_repository.py)
- [tests/tools/minecraft/mission/test_schema_bundle.py](../../tests/tools/minecraft/mission/test_schema_bundle.py)
- [tests/tools/minecraft/mission/test_state_machine.py](../../tests/tools/minecraft/mission/test_state_machine.py)
- [tests/tools/minecraft/mission/test_verifier.py](../../tests/tools/minecraft/mission/test_verifier.py)

#### tests/tools/minecraft/showcase

- [tests/tools/minecraft/showcase/__init__.py](../../tests/tools/minecraft/showcase/__init__.py)
- [tests/tools/minecraft/showcase/test_bounded_feedback.py](../../tests/tools/minecraft/showcase/test_bounded_feedback.py)
- [tests/tools/minecraft/showcase/test_dialogue_regression.py](../../tests/tools/minecraft/showcase/test_dialogue_regression.py)
- [tests/tools/minecraft/showcase/test_historical_audit.py](../../tests/tools/minecraft/showcase/test_historical_audit.py)
- [tests/tools/minecraft/showcase/test_live_evidence.py](../../tests/tools/minecraft/showcase/test_live_evidence.py)
- [tests/tools/minecraft/showcase/test_micro_gates.py](../../tests/tools/minecraft/showcase/test_micro_gates.py)
- [tests/tools/minecraft/showcase/test_presentation.py](../../tests/tools/minecraft/showcase/test_presentation.py)
- [tests/tools/minecraft/showcase/test_projection_relay.py](../../tests/tools/minecraft/showcase/test_projection_relay.py)
- [tests/tools/minecraft/showcase/test_promotion.py](../../tests/tools/minecraft/showcase/test_promotion.py)
- [tests/tools/minecraft/showcase/test_real_model_contract.py](../../tests/tools/minecraft/showcase/test_real_model_contract.py)
- [tests/tools/minecraft/showcase/test_runner.py](../../tests/tools/minecraft/showcase/test_runner.py)
- [tests/tools/minecraft/showcase/test_scenario.py](../../tests/tools/minecraft/showcase/test_scenario.py)
- [tests/tools/minecraft/showcase/test_script_summary.py](../../tests/tools/minecraft/showcase/test_script_summary.py)
- [tests/tools/minecraft/showcase/test_stage_projector.py](../../tests/tools/minecraft/showcase/test_stage_projector.py)

#### tests/tools/minecraft/skill

- [tests/tools/minecraft/skill/__init__.py](../../tests/tools/minecraft/skill/__init__.py)
- [tests/tools/minecraft/skill/test_acquisition_skill_reuse.py](../../tests/tools/minecraft/skill/test_acquisition_skill_reuse.py)
- [tests/tools/minecraft/skill/test_applicability_selection.py](../../tests/tools/minecraft/skill/test_applicability_selection.py)
- [tests/tools/minecraft/skill/test_craft_integration.py](../../tests/tools/minecraft/skill/test_craft_integration.py)
- [tests/tools/minecraft/skill/test_extractor.py](../../tests/tools/minecraft/skill/test_extractor.py)
- [tests/tools/minecraft/skill/test_independent_validation.py](../../tests/tools/minecraft/skill/test_independent_validation.py)
- [tests/tools/minecraft/skill/test_planner_skill_integration.py](../../tests/tools/minecraft/skill/test_planner_skill_integration.py)
- [tests/tools/minecraft/skill/test_predefined_skills.py](../../tests/tools/minecraft/skill/test_predefined_skills.py)
- [tests/tools/minecraft/skill/test_revision_trust.py](../../tests/tools/minecraft/skill/test_revision_trust.py)
- [tests/tools/minecraft/skill/test_skill_applicability.py](../../tests/tools/minecraft/skill/test_skill_applicability.py)
- [tests/tools/minecraft/skill/test_skill_ir.py](../../tests/tools/minecraft/skill/test_skill_ir.py)
- [tests/tools/minecraft/skill/test_skill_library.py](../../tests/tools/minecraft/skill/test_skill_library.py)
- [tests/tools/minecraft/skill/test_skill_matching.py](../../tests/tools/minecraft/skill/test_skill_matching.py)
- [tests/tools/minecraft/skill/test_skill_step.py](../../tests/tools/minecraft/skill/test_skill_step.py)
- [tests/tools/minecraft/skill/test_skill_trust_matching.py](../../tests/tools/minecraft/skill/test_skill_trust_matching.py)
- [tests/tools/minecraft/skill/test_skill_trust_persistence.py](../../tests/tools/minecraft/skill/test_skill_trust_persistence.py)
- [tests/tools/minecraft/skill/test_skill.py](../../tests/tools/minecraft/skill/test_skill.py)
- [tests/tools/minecraft/skill/test_validator.py](../../tests/tools/minecraft/skill/test_validator.py)

#### tests/tools/minecraft/survival

- [tests/tools/minecraft/survival/__init__.py](../../tests/tools/minecraft/survival/__init__.py)
- [tests/tools/minecraft/survival/test_benchmark.py](../../tests/tools/minecraft/survival/test_benchmark.py)
- [tests/tools/minecraft/survival/test_inventory.py](../../tests/tools/minecraft/survival/test_inventory.py)
- [tests/tools/minecraft/survival/test_models.py](../../tests/tools/minecraft/survival/test_models.py)
- [tests/tools/minecraft/survival/test_recovery.py](../../tests/tools/minecraft/survival/test_recovery.py)

#### tests/tools/minecraft/tech_tree

- [tests/tools/minecraft/tech_tree/__init__.py](../../tests/tools/minecraft/tech_tree/__init__.py)

#### tests/tools/minecraft/voyager

- [tests/tools/minecraft/voyager/test_advancement_store.py](../../tests/tools/minecraft/voyager/test_advancement_store.py)
- [tests/tools/minecraft/voyager/test_bounded_strategies.py](../../tests/tools/minecraft/voyager/test_bounded_strategies.py)
- [tests/tools/minecraft/voyager/test_command_executor.py](../../tests/tools/minecraft/voyager/test_command_executor.py)
- [tests/tools/minecraft/voyager/test_command_journal.py](../../tests/tools/minecraft/voyager/test_command_journal.py)
- [tests/tools/minecraft/voyager/test_control_plane_evidence.py](../../tests/tools/minecraft/voyager/test_control_plane_evidence.py)
- [tests/tools/minecraft/voyager/test_control_plane_models.py](../../tests/tools/minecraft/voyager/test_control_plane_models.py)
- [tests/tools/minecraft/voyager/test_events_projection.py](../../tests/tools/minecraft/voyager/test_events_projection.py)
- [tests/tools/minecraft/voyager/test_fault_harness.py](../../tests/tools/minecraft/voyager/test_fault_harness.py)
- [tests/tools/minecraft/voyager/test_gateway.py](../../tests/tools/minecraft/voyager/test_gateway.py)
- [tests/tools/minecraft/voyager/test_goal_verifier.py](../../tests/tools/minecraft/voyager/test_goal_verifier.py)
- [tests/tools/minecraft/voyager/test_mocked_cross_runtime.py](../../tests/tools/minecraft/voyager/test_mocked_cross_runtime.py)
- [tests/tools/minecraft/voyager/test_public_activity.py](../../tests/tools/minecraft/voyager/test_public_activity.py)
- [tests/tools/minecraft/voyager/test_real_e2e_harness.py](../../tests/tools/minecraft/voyager/test_real_e2e_harness.py)
- [tests/tools/minecraft/voyager/test_reconciliation_matrix.py](../../tests/tools/minecraft/voyager/test_reconciliation_matrix.py)
- [tests/tools/minecraft/voyager/test_scheduler_stop.py](../../tests/tools/minecraft/voyager/test_scheduler_stop.py)
- [tests/tools/minecraft/voyager/test_tech_graph.py](../../tests/tools/minecraft/voyager/test_tech_graph.py)

#### tests/tracing

- [tests/tracing/__init__.py](../../tests/tracing/__init__.py)
- [tests/tracing/test_proxy.py](../../tests/tracing/test_proxy.py)

#### tests/unit

- [tests/unit/test_tts_qwen3.py](../../tests/unit/test_tts_qwen3.py)

#### tests/utils

- [tests/utils/__init__.py](../../tests/utils/__init__.py)
- [tests/utils/test_auto_config.py](../../tests/utils/test_auto_config.py)
- [tests/utils/test_env_helper.py](../../tests/utils/test_env_helper.py)
- [tests/utils/test_logger_manager.py](../../tests/utils/test_logger_manager.py)

### tooling

#### tooling

- [tooling/__init__.py](../../tooling/__init__.py)
- [tooling/quality.yml](../../tooling/quality.yml)
- [tooling/runtime_startup.py](../../tooling/runtime_startup.py)

#### tooling/bilibili_mcp

- [tooling/bilibili_mcp/__init__.py](../../tooling/bilibili_mcp/__init__.py)
- [tooling/bilibili_mcp/__main__.py](../../tooling/bilibili_mcp/__main__.py)
- [tooling/bilibili_mcp/controller.py](../../tooling/bilibili_mcp/controller.py)
- [tooling/bilibili_mcp/server.py](../../tooling/bilibili_mcp/server.py)

#### tooling/execution_feedback

- [tooling/execution_feedback/__init__.py](../../tooling/execution_feedback/__init__.py)
- [tooling/execution_feedback/__main__.py](../../tooling/execution_feedback/__main__.py)
- [tooling/execution_feedback/cli.py](../../tooling/execution_feedback/cli.py)
- [tooling/execution_feedback/failures.py](../../tooling/execution_feedback/failures.py)
- [tooling/execution_feedback/leases.py](../../tooling/execution_feedback/leases.py)
- [tooling/execution_feedback/lifecycle.py](../../tooling/execution_feedback/lifecycle.py)
- [tooling/execution_feedback/minecraft.py](../../tooling/execution_feedback/minecraft.py)
- [tooling/execution_feedback/models.py](../../tooling/execution_feedback/models.py)
- [tooling/execution_feedback/plan.py](../../tooling/execution_feedback/plan.py)
- [tooling/execution_feedback/process_runner.py](../../tooling/execution_feedback/process_runner.py)
- [tooling/execution_feedback/store.py](../../tooling/execution_feedback/store.py)
- [tooling/execution_feedback/supervisor.py](../../tooling/execution_feedback/supervisor.py)

#### tooling/quality

- [tooling/quality/__init__.py](../../tooling/quality/__init__.py)
- [tooling/quality/__main__.py](../../tooling/quality/__main__.py)
- [tooling/quality/aggregate.py](../../tooling/quality/aggregate.py)
- [tooling/quality/architecture_boundaries.py](../../tooling/quality/architecture_boundaries.py)
- [tooling/quality/benchmark.py](../../tooling/quality/benchmark.py)
- [tooling/quality/cache.py](../../tooling/quality/cache.py)
- [tooling/quality/change_sources.py](../../tooling/quality/change_sources.py)
- [tooling/quality/cli.py](../../tooling/quality/cli.py)
- [tooling/quality/docker_plan.py](../../tooling/quality/docker_plan.py)
- [tooling/quality/evidence.py](../../tooling/quality/evidence.py)
- [tooling/quality/executor.py](../../tooling/quality/executor.py)
- [tooling/quality/feedback.py](../../tooling/quality/feedback.py)
- [tooling/quality/fingerprint.py](../../tooling/quality/fingerprint.py)
- [tooling/quality/hashing.py](../../tooling/quality/hashing.py)
- [tooling/quality/image_fingerprint.py](../../tooling/quality/image_fingerprint.py)
- [tooling/quality/manifest.py](../../tooling/quality/manifest.py)
- [tooling/quality/minecraft_architecture.py](../../tooling/quality/minecraft_architecture.py)
- [tooling/quality/models.py](../../tooling/quality/models.py)
- [tooling/quality/npm_runner.py](../../tooling/quality/npm_runner.py)
- [tooling/quality/path_matching.py](../../tooling/quality/path_matching.py)
- [tooling/quality/planner.py](../../tooling/quality/planner.py)
- [tooling/quality/scheduler.py](../../tooling/quality/scheduler.py)
- [tooling/quality/warm_topology.py](../../tooling/quality/warm_topology.py)
