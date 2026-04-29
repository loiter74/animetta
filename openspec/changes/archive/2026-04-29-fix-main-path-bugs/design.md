## Context

后端主链路有 3 类 bug：
1. **Import 路径错误**：VAD/LLM 工厂引用不存在的 `implementations/` 子目录，模块重构后遗留
2. **output_node 功能缺失**：LangGraph 迁移后，output_node 只转发文本和音频，丢失了 expression/volumes/control 信号
3. **无测试覆盖**：主链路无自动化测试，bug 无法被 CI 捕获

现有测试只有 `tests/test_stats_store.py`（1 个文件），项目使用 pytest + pytest-asyncio。

## Goals / Non-Goals

**Goals:**
- 修复全部 6 个主链路 bug，恢复语音输入、口型同步、表情推送、控制信号
- 新增 6 个自动化测试覆盖修复点
- 测试不依赖外部 API 或 GPU 模型

**Non-Goals:**
- 不重构 VAD/LLM 工厂的整体架构
- 不修改前端代码（前端事件监听已正确，只缺后端发送）
- 不新增功能，只修复已有功能的 bug

## Decisions

### D1: VAD/LLM import 路径统一为直接子模块导入

**选择**：`from .mock_vad import MockVAD`（直接导入）
**替代方案**：创建 `implementations/` 子目录并移动文件
**理由**：LLM 模块已经用直接导入且运行正常，保持一致。创建子目录增加不必要的目录层级。

### D2: output_node 使用 AudioAnalyzer 计算 volumes

**选择**：在 output_node 中当 TTS 返回文件路径时，调用 `AudioAnalyzer.compute_volume_envelope()` 计算 volumes 数组，附加到 `audio_with_expression` 事件
**替代方案**：在前端做音频分析
**理由**：后端已有 `AudioAnalyzer` 工具类，计算一次即可。前端环境（Electron renderer）做音频分析会增加延迟和复杂度。

### D3: expression 事件复用已有格式

**选择**：发送 `{"action": "set_expression", "expression": emotion}` 事件名 `expression`
**理由**：前端 `IpcBridge` 已有 `live2d.action` → `live2d:action` 的转发链路，直接复用。

### D4: control 信号格式

**选择**：`emit("control", {"signal": "conversation-start"})` 和 `emit("control", {"signal": "conversation-end"})`
**理由**：与 `IpcBridge:112-117` 已有的监听逻辑完全匹配，无需前端改动。

## Risks / Trade-offs

- **[风险] AudioAnalyzer 依赖 pydub** → 降级处理：如果 pydub 不可用，跳过 volumes 计算，前端无口型但不会崩溃
- **[风险] 临时文件清理** → output_node 读取 TTS 临时文件后无需手动清理（TTS 引擎自行管理）
- **[权衡] 测试使用 mock 而非真实模型** → 牺牲端到端真实性换取 CI 可靠性和速度，可接受
