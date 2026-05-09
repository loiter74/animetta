## 1. Install Miniconda

- [x] 1.1 Download Miniconda3 Windows installer (Tsinghua mirror)
- [x] 1.2 Install to `~/miniconda3` with silent install
- [x] 1.3 Verify `conda` command available — conda 26.3.2 ✓

## 2. Create GPT-SoVITS Environment

- [x] 2.1 Create env: `conda create -n gpt-sovits python=3.10 -y` ✅
- [x] 2.2 Install cu128 PyTorch: torch 2.11.0+cu128 ✅ (downloaded via Aliyun mirror)
- [x] 2.3 Verify CUDA: 5090D, sm_120 in arch list ✅
- [x] 2.4 Install GPT-SoVITS deps from requirements.txt ✅
- [x] 2.5 Apply code patches (Tuple import, weights_only=False) ✅
- [x] 2.6 Install onnxruntime-gpu==1.22.0 (Blackwell compat) ✅
- [x] 2.7 Configure tts_infer.yaml with Evil V2 weights ✅
- [x] 2.8 Test with curl: verify TTS endpoint works — HTTP 200, valid WAV audio ✅

## 3. Create Anima Environment (已取消 — 保持现有 .venv 不变)

- [x] 3.1 Create env: `conda create -n anima python=3.13 -y` — 已取消，用户决定不迁移
- [x] 3.2 Install deps: `pip install -r requirements.txt` — 已取消
- [x] 3.3 Update `config.yaml` — set `system.gpt_sovits.path` + `system.gpt_sovits.python` ✅

## 4. Verification

- [x] 4.1 Run `python scripts/start.py` — GPT-SoVITS server starts, Anima backend connects ✅
- [x] 4.2 Send test message in chat — TTS works end-to-end, 404KB audio, HTTP 200 ✅
