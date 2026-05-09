## 1. 同步 XML 人设内容

- [x] 1.1 XML 内容已经是分析师风格（此前已修改），保留 XML 作为提示词多样化源 ✅

## 2. 清理冗余文件

- [x] 2.1 已删除 `ref_text.txt`（内容在 services.yaml 中）✅
- [x] 2.2 已确认：`ref_audio.wav`(英)、`ref_audio_zh.wav`(中)、`tts_infer.yaml` 均为必要文件 ✅

## 3. 验证

- [x] 3.1 `PersonaConfig.load('neuro-vtuber')` → Name=Neuro, Role=数据分析师/策略顾问 ✅
- [x] 3.2 `base.py` 语法检查通过，AppConfig 可正常加载 ✅
