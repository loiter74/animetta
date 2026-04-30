## Why

前端目前缺少 favicon、配置面板不显示真实服务数据、背景纯色不可自定义，整体体验粗糙。需要一次集中优化补齐这些基础体验缺失。

## What Changes

- 添加浏览器 favicon（SVG）
- 添加自定义背景图功能（URL 输入 + 文件上传 + 预设背景库），设置存储于 localStorage
- 设置面板从后端获取真实配置并显示（ASR/TTS/LLM/VAD 服务名、角色名、模型信息）
- 后端新增 `get_config` → `config_data` socket 事件暴露配置（剔除 API Key）
- 添加记忆整理状态详情显示
- 添加重置 Live2D 视图按钮

## Capabilities

### New Capabilities
- `favicon`: 浏览器标签页图标
- `custom-background`: 自定义背景图设置（URL/上传/预设），存储于 localStorage
- `settings-config-display`: 设置面板显示后端实时配置数据
- `memory-organize-status`: 记忆整理过程状态展示
- `live2d-view-reset`: 一键重置 Live2D 缩放和位置

### Modified Capabilities
- （无现有 spec 变更）

## Impact

- **前端**: 修改 `index.html`、`App.vue`、`SettingsPanel.vue`、`Live2DRenderer.vue`、`InteractivePanel.vue`，新建 `BackgroundSettings.vue` 组件
- **后端**: 修改 `routes.py`，新增 `on_get_config` handler
- **资源**: 新增 SVG favicon 和预设背景图片到 `frontend/public/`
- **无 Breaking Changes**
