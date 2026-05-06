## Context

启动脚本 `scripts/start.py` 刚完成模块化重构（提取为 `scripts/start/` 包），但默认行为仍是 `desktop` 模式，只启动 backend + web config。用户需要 `--mode web` 才能启动 Vite 前端。造成混淆：不同模式启动不同服务组合，且 web config 配置页因路径问题返回 404。

## Goals / Non-Goals

**Goals:**
- `python scripts/start.py` 一键启动所有服务：backend(12394) + Vite frontend(3000) + web config(8080)
- 浏览器自动打开三个可访问页面
- 移除 `--mode` 参数，合并为统一行为
- 新增 `--no-frontend` 替代旧的 `--no-app` 语义
- 保留 `--backend-only`、`--no-backend`、`--no-web-config` 兼容

**Non-Goals:**
- 不涉及 `stop.py` 改动
- 不涉及 Electron 桌面应用启动方式变更
- 不新增服务类型

## Decisions

| Decision | Rationale |
|----------|-----------|
| **移除 `--mode`** | 两个模式的行为差异是历史遗留（原 Electron 有桌面端）。现在统一为一个命令启动所有 |
| **`--no-frontend` 替代 `--no-app`** | `--no-app` 语义模糊（desktop app 还是 web frontend？）|
| **保留 `--backend-only`** | 兼容已有工作流，对开发调试有用 |
| **保留 `--no-web-config`** | 非必需时跳过 8080 配置页 |
| **自动打开页面延迟 2/3/4 秒** | Vite 启动最慢（5-10s），最后打开确保可用 |

启动流程：
```
python scripts/start.py
  → 1. 停止旧服务 (12394, 8765, 8080, 3000)
  → 2. (可选) VibeVoice TTS → 8765
  → 3. Backend → 12394
  → 4. Web Config → 8080
  → 5. Vite Frontend → 3000
  → 6. 自动打开浏览器 (health → config → frontend)
```

## Risks / Trade-offs

- **[Risk] Vite 启动慢 (5-10s)** → 浏览器延迟 4s 后再打开 frontend
- **[Risk] `--no-app` 兼容** → 映射到 `--no-frontend` 仍可用
- **[Risk] Electron 用户习惯变化** → 添加 `--mode desktop` 别名（但打印 deprecation warning）
