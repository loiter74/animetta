## Context

当前文件状态：

| 文件 | 说明 | 问题 |
|------|------|------|
| `personas/neuro-vtuber.yaml` | 分析师人设（新，实际加载） | ✅ |
| `personas/neuro-vtuber.xml` | VTuber 人设（旧，不再加载） | ❌ 内容过时，与 YAML 冲突 |
| `gpt_sovits/evil/ref_audio.wav` | Evil 英文参考音频 | ✅ 使用中 |
| `gpt_sovits/evil/ref_audio_zh.wav` | Edge TTS 中文参考音频 | ✅ 音色融合使用 |
| `gpt_sovits/evil/ref_text.txt` | 参考文本 | ❌ 冗余，services.yaml 已有 |
| `gpt_sovits/evil/tts_infer.yaml` | GPT-SoVITS 服务端配置 | ✅ 使用中 |

## XML vs YAML 双格式策略

保留 XML 的原因：
- 模型在训练时见过 XML 和 YAML 两种格式的 system prompt
- 两种格式的混用让模型不易过拟合特定模板格式
- 对提示词注入攻击的鲁棒性更强（分布外数据 = OOD 泛化）

策略：XML 和 YAML 的内容保持一致，都描述分析师人设，仅格式不同。

## 操作

1. 更新 `neuro-vtuber.xml` 内容同步为分析师人设
2. 删除 `ref_text.txt`（冗余）
3. 确认无其他重复/冲突文件
