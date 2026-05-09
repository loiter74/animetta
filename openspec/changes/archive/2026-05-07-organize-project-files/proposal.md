## Why

项目经过多轮迭代积累了不少冗余文件：两种格式的人设文件内容不一致、参考音频有英文和中文两份但目录结构不清晰、根目录混入了文档和脚本。整理目录结构，保持 XML 人设作为提示词多样化的补充。

## What Changes

- 保留 XML + YAML 双格式人设，同步 XML 内容为分析师风格（避免老 VTuber 人设残留）
- 整理 `config/gpt_sovits/` 目录结构
- 清理冗余文件（`ref_text.txt` 内容已包含在 `services.yaml` 中）
- 确认 `build_system_prompt()` 同时支持 XML 和 YAML 两种人设源

## Capabilities

### New Capabilities
- `project-file-organization`: 项目文件整理，去除冗余，保持双格式人设一致性

### Modified Capabilities
- None

## Impact
- **Modified**: `config/personas/neuro-vtuber.xml` — 同步为分析师人设
- **Removed**: `config/gpt_sovits/evil/ref_text.txt` — 冗余，内容在 services.yaml
- **Directory**: `config/gpt_sovits/evil/` 保留英文/中文两份参考音频
