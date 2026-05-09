## 1. Apply Anima Configuration Changes

- [x] 1.1 Update `config/services.yaml` — add `gpt_sovits_evil` provider entry with ref_audio_path, prompt_text, English language settings
- [x] 1.2 Update `config/config.yaml` — change `services.tts` from `kokoro_glados` to `gpt_sovits_evil`

## 2. Create GPT-SoVITS Server Config

- [x] 2.1 Documented in design.md — tts_infer.yaml template for Evil V2 weights (t2s_weights_path, vits_weights_path)

## 3. Verify

- [x] 3.1 YAML configs validated — both files parse correctly
- [x] 3.2 gpt_sovits_evil profile confirmed with correct ref_audio_path and en/en language
- [x] 3.3 Start GPT-SoVITS api_v2.py with Evil model — server started, models loaded, uvicorn listening on :9880 ✅
- [x] 3.4 Test with curl to /tts — HTTP 200, valid WAV audio returned ✅
- [x] 3.5 Start Anima — TTS connected and generated 404KB audio ✅