## Why

后端主链路存在 6 个阻塞性 bug，导致语音输入无响应、Live2D 嘴唇不动、前端状态不重置。这些都是用户直接可感知的功能缺陷，需要立即修复并通过自动化测试覆盖防止回归。

## What Changes

- **修复 VAD 模块 import 路径**：`vad/__init__.py` 和 `vad/factory.py` 中 `from .implementations.xxx` 指向不存在的子目录，改为 `from .xxx` 直接导入，恢复 VAD 服务注册（Bug 1-2）
- **修复 LLM 工厂降级路径**：`llm/factory.py` 中降级导入同样指向 `implementations/`，改为直接导入 `mock_llm`（Bug 3）
- **补全 output_node 表情推送**：在 `output_node.py` 中读取 emotion 状态并发送 `expression` 事件到前端（Bug 4）
- **补全 output_node 音量包络**：在 `output_node.py` 中使用 `AudioAnalyzer` 计算 volumes 并附加到 `audio_with_expression`（Bug 5）
- **补全 output_node 控制信号**：在 `output_node.py` 中发送 `conversation-start` 和 `conversation-end` 控制信号（Bug 6）
- **新增 6 个自动化测试**覆盖以上修复

## Capabilities

### New Capabilities
- `main-path-tests`: 主链路 bug 修复的自动化测试，覆盖服务注册、工厂降级、output_node 事件推送

### Modified Capabilities

## Impact

- `src/anima/services/intelligence/vad/` — `__init__.py`, `factory.py` import 路径
- `src/anima/services/intelligence/llm/` — `factory.py` 降级路径
- `src/anima/orchestration/graph/output_node.py` — 新增 expression/volumes/control 发送逻辑
- `tests/test_main_path.py` — 新增测试文件
