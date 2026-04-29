## 1. 修复 VAD import 路径

- [x] 1.1 修复 `vad/__init__.py:10`：`from .implementations import mock_vad, silero_vad` → `from . import silero_vad, mock_vad`
- [x] 1.2 修复 `vad/factory.py`：所有 6 处 `from .implementations.xxx` → `from .xxx`（行 38, 63, 75, 84, 89, 98）

## 2. 修复 LLM 降级路径

- [x] 2.1 修复 `llm/factory.py:52`：`from .implementations.mock_llm` → `from .mock_llm`

## 3. 补全 output_node 事件推送

- [x] 3.1 在 output_node 顶部添加 `conversation-start` 发送逻辑（在文本/音频推送之前）
- [x] 3.2 在 output_node 中添加 emotion → expression 事件发送（读取 `state["emotion"]`）
- [x] 3.3 在 output_node 中添加 volumes 计算：当 `tts_audio` 为文件路径时，调用 `AudioAnalyzer.compute_volume_envelope()` 并附加到 `audio_with_expression`
- [x] 3.4 在 output_node 末尾添加 `conversation-end` 发送逻辑

## 4. 编写自动化测试

- [x] 4.1 `test_vad_services_registered`：验证 VAD silero + mock 注册成功
- [x] 4.2 `test_vad_factory_fallback_to_mock`：验证 VAD 创建失败降级到 MockVAD
- [x] 4.3 `test_llm_factory_fallback_to_mock`：验证 LLM 创建失败降级到 MockLLM
- [x] 4.4 `test_output_node_sends_expression`：验证 output_node 发送 expression 事件
- [x] 4.5 `test_output_node_sends_volumes`：验证 audio_with_expression 包含 volumes
- [x] 4.6 `test_output_node_sends_control_signals`：验证 conversation-start/end 控制信号
