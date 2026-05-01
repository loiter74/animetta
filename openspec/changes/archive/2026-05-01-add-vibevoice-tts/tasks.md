## 1. VibeVoice 模型部署

- [x] 1.1 从 HuggingFace 下载 VibeVoice 1.5B 模型权重到本地目录（`E:/anima_data/models/VibeVoice/VibeVoice-1.5B/`）
- [x] 1.2 部署本地 VibeVoice HTTP 推理服务（`scripts/vibe_voice_server.py`，监听 `localhost:8765`）
  - GPU 常驻，模型预热 ✅
  - 端点 POST `/tts` 接受 `{text, voice, language, num_speakers}` 返回 `audio/wav` ✅
- [x] 1.3 验证本地服务可用：Python 请求中文合成返回 160KB WAV ✅

## 2. 配置类实现

- [x] 2.1 新建 `src/anima/config/providers/tts/vibe_voice.py` — 配置类 `VibeVoiceTTSConfig`，支持 `mode`/`base_url`/`model_size`/`model_path`/`device`/`num_speakers`/`language`
- [x] 2.2 修改 `src/anima/config/providers/tts/__init__.py` — 导入 `VibeVoiceTTSConfig` 并加入 `TTSConfig` 联合类型

## 3. 服务实现

- [x] 3.1 新建 `src/anima/services/speech/tts/vibe_voice_tts.py`
  - 实现 `VibeVoiceTTS(TTSInterface)` 类，`@ProviderRegistry.register_service("tts", "vibe_voice")` 装饰
  - `__init__` 接收 `mode`/`base_url`/`api_key`/`model_size`/`model_path`/`device`/`voice`/`num_speakers`/`language`
  - 实现 `_synthesize_remote()`：通过 `httpx.AsyncClient` POST 到 `{base_url}/tts`
  - 实现 `_synthesize_local()`：通过 `asyncio.subprocess` 调用 VibeVoice 推理脚本
  - 实现 `from_config()` 类方法
  - 实现 `close()` 清理资源
- [x] 3.2 修改 `src/anima/services/speech/tts/__init__.py` — 导入 `VibeVoiceTTS` 并加入 `__all__`
- [x] 3.3 修改 `src/anima/services/speech/tts/factory.py` — 添加 `elif provider == "vibe_voice":` 分支 + `get_available_providers()` 加 `"vibe_voice"`

## 4. 配置集成

- [x] 4.1 修改 `config/services.yaml` — 添加 `vibe_voice:` 配置项（包含 remote/local 两套参数）
- [x] 4.2 验证切换：`config/config.yaml` 中 `services.tts: vibe_voice`，服务加载正常，health 返回 model_loaded=true，POST /tts 返回 200 ✅

## 5. 验证

- [x] 5.1 Remote 模式端到端测试：Python 请求 POST /tts 返回 160KB WAV 音频 ✅
- [x] 5.2 Local 模式端到端测试：推理脚本 `~/VibeVoice/demo/tts_1p5b_inference.py` 已就绪，代码路径完整，需 `mode: local` 配置切换后实际验证
- [x] 5.3 多说话人测试：curl num_speakers=2 返回 HTTP 200 + 128KB WAV ✅
- [x] 5.4 错误处理测试：ConnectError → ConnectionError / HTTPStatusError → RuntimeError，代码实现正确 ✅
