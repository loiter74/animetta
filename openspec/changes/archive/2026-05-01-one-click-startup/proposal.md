## Why

当前启动脚本需要用户记住 `--mode web` 等参数，不同模式启动不同服务组合。用户期望一个命令启动所有服务（后端 + Vue 前端 + Web 配置页），浏览器自动打开可访问的页面。之前的体验中，8080 返回 404、3000 拒绝连接、自动打开不生效等问题反复出现。

## What Changes

- **默认模式改为启动全部服务**：`python scripts/start.py` 同时启动 backend(12394) + Vite frontend(3000) + web config(8080)
- **移除 `--mode` 参数**：不再区分 desktop/web 模式，一个命令启动所有
- **修复 web config 配置页**：确保 `frontend/web/templates/config.html` 存在并可访问
- **自动打开所有可访问页面**：浏览器自动打开 health check + web config + Vite frontend
- **新增 `--no-frontend` 参数**：允许跳过前端启动（替代旧的 `--mode desktop` + `--no-app`）

## Capabilities

### New Capabilities
- `one-click-startup`: 一键启动所有服务（backend + frontend + web config），默认行为

### Modified Capabilities
<!-- No existing specs modified -->

## Impact

- `scripts/start.py` — 主入口，修改默认行为和参数
- `scripts/start/services.py` — 启动逻辑调整
- `scripts/start/browser.py` — 自动打开逻辑
- `frontend/web/templates/config.html` — 配置页（已存在）
