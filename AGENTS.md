# ANIMA PROJECT KNOWLEDGE BASE

**Generated:** 2026-05-10
**Commit:** ff90d6d
**Branch:** main

> Primary knowledge base: [CLAUDE.md](CLAUDE.md). This AGENTS.md is the quick-reference map.

## OVERVIEW

AI virtual companion / VTuber framework. Python backend (FastAPI + LangGraph + Socket.IO) + Vue 3 Electron frontend + Live2D avatar.

## STRUCTURE

```
./
├── src/anima/              # Python backend (223 files, 35.8K lines)
│   ├── core/               # Entry point + service container
│   ├── orchestration/      # LangGraph state graph + WebSocket server
│   ├── services/           # LLM / ASR / TTS / VAD implementations
│   ├── memory/             # Wiki-architecture memory (Chroma + SQLite)
│   ├── config/             # Pydantic configs + provider registry
│   ├── avatar/             # Live2D emotion/expression analysis
│   ├── tools/              # Tool calling + MCP bridge
│   └── utils/              # Helpers
├── frontend/               # Vue 3 + TypeScript + Electron (UnoCSS, Pinia)
├── config/                 # YAML config files (personas, services, tools)
├── tests/                  # pytest suite (131 test files, 2136 tests)
├── docs/                   # ADRs, plans, benchmarks
├── scripts/                # start.py, stop.py, etc.
└── .claude/                # Claude skills
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add LLM provider | `src/anima/services/intelligence/llm/` | Create class, register via `@ProviderRegistry` |
| Add ASR/TTS provider | `src/anima/services/speech/{asr,tts}/` | Same pattern as LLM |
| Add graph node | `src/anima/orchestration/graph/` | Follow node pattern in `__init__.py` |
| Add tool | `src/anima/tools/base.py` or `custom_tools.py` | Use `@tool` decorator |
| Add persona | `config/personas/` + `src/anima/config/persona/` | YAML + Pydantic |
| Fix WebSocket route | `src/anima/orchestration/server/routes.py` | **1377 lines - largest file** |
| Change memory behavior | `src/anima/memory/` | Wiki architecture, see ADR-005 |
| Fix Live2D expression | `src/anima/avatar/` + `frontend/src/components/live2d/` | |
| Run tests | `PYTHONPATH=src python -m pytest tests/ -v` | asyncio_mode=auto |
| Type check | `mypy src/ --ignore-missing-imports` | |

## CONVENTIONS

- **Python 3.13+** — `X | None` not `Optional[X]`
- **Pydantic V2** — `model_config = ConfigDict(...)` not `class Config:`
- **Async-first** — all I/O is async
- **Type hints required** on all public functions
- **Logging**: `loguru` logger, English only
- **Provider plugin pattern**: `interface.py` ABC → implementations → factory → `__init__.py` re-exports
- **TDD preferred** — write tests first

## ANTI-PATTERNS (THIS PROJECT)

- ❌ Never import from removed modules: `pipeline/`, `events/`, `handlers/`, `adapters/`, old `core/`, `services/conversation/`, old `state/`
- ❌ Never rewrite business logic in graph nodes — reuse `services/` implementations
- ❌ Never call `ctx.close()` on ServicePool — destroys shared LLM/TTS/ASR engines
- ❌ Never use real-time `getBounds()` in Live2D scaling — use cached `baseBounds`
- ❌ Never add EventBus back — LangGraph is the only orchestration mode (ADR-001)
- ❌ Pydantic V2 only — `class Config:` is forbidden

## COMMANDS

```bash
# Start all services
python scripts/start.py

# Backend only
python -m anima.socketio_server

# Tests
PYTHONPATH=src python -m pytest tests/ -v
PYTHONPATH=src python -m pytest tests/ --cov=src/anima --cov-report=term-missing

# Type + lint
mypy src/ --ignore-missing-imports
ruff check src/ tests/
```

## Model Selection Strategy

Two DeepSeek models are available via `oh-my-openagent.json`:

| Model | Agent/Category | Role |
|-------|---------------|------|
| **flash** (`deepseek/deepseek-v4-flash`) | sisyphus, sisyphus-junior, explore, librarian, visual-engineering, quick, unspecified-low, unspecified-high, writing | 快速、低成本，适合确定性强的任务 |
| **pro** (`deepseek/deepseek-v4-pro`) | oracle, prometheus, metis, momus, ultrabrain, deep, artistry | 高推理能力，适合复杂/不确定/高代价场景 |

### Decision Matrix

When delegating an implementation task (always use `deep` or `unspecified-high`), choose:

| 场景 | Use | 模型 |
|------|-----|------|
| 改一个文件、模式已知、改什么怎么写很清楚 | `unspecified-high` | flash |
| 跨 2+ 模块、需要理解代码结构 | `deep` | **pro** |
| 新功能设计、需要做 trade-off 选型 | `deep` | **pro** |
| 批量执行、但每步逻辑简单（如替换字符串、加字段） | `unspecified-high` | flash |
| 调试复杂 bug、需要追踪调用链 | `deep` or `oracle` | **pro** |
| 纯搜索/查找（不修改代码） | `explore` / `librarian` | flash |
| 纯 UI 视觉任务 | `visual-engineering` | flash |
| 单文件 typo/简单修改 | `quick` | flash |
| 硬核逻辑、算法、数学 | `ultrabrain` | **pro** |
| 非常规思路、需要跳出框架 | `artistry` | **pro** |

**Rule of thumb:** 如果不确定是 `deep` 还是 `unspecified-high`，选 `deep`（pro）。宁可贵一点，不要因为模型不够强而反复重做。

### Pro Trigger Examples

以下情况**必须**用 pro 类别（`deep` / `ultrabrain` / `oracle`）：

- **首次接触的代码模块**——不熟悉内部结构，需要 pro 理解上下文
- **跨 2 个以上模块的改动**——需要全局推理保证一致性
- **设计/选型决策**——架构方案、API 设计、数据流设计
- **复杂调试**——2 次尝试没解决的 bug
- **高代价区域**——核心逻辑、对外接口、生产关键路径
- **模棱两可的需求**——用户没说清楚，需要推理多种可能性

以下情况**可以**用 flash 类别（`unspecified-high` / `quick` / `explore`）：

- **搜索/查找**——找文件、找模式、找定义
- **已知模式的重复操作**——加个字段、改个类型、复制已有模式
- **纯执行**——实现方案已经定好了，只差写代码
- **低风险修改**——工具脚本、测试辅助、注释文档

## NOTES

- `orchestration/server/routes.py` at 1377 lines is a known hotspot — thin dispatch preferred
- Backend coverage at ~70%, targeting 70%. Frontend test coverage: 0% (being set up).
- 5 ADRs in `docs/adrs/`: LangGraph, Hybrid Search, Plugin Architecture, Streaming, Wiki Memory
