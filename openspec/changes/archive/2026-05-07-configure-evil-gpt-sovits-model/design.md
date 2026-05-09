## Context

Existing `gpt_sovits` TTS provider has been integrated into Anima. The user has trained an "Evil" voice model (English-speaking VTuber style character) with GPT-SoVITS V2, with reference audio and trained weights on disk.

## Model Details

| Item | Value |
|------|-------|
| Model name | Evil |
| Language | English |
| Model version | GPT-SoVITS V2 |
| Reference audio | `E:\BaiduNetdiskDownload\Model\Evil\参考语音.wav` (5.9s, 32kHz mono WAV) |
| Reference text | `I played Shovel Knight once. It turns out AI doesn't exactly have perfect hand-eye coordination.` |

### Recommended Weights (V2)

For best quality, use mid-training checkpoints (not underfitted, not overfitted):

- **GPT weights**: `Evil-e15.ckpt` (149 MB, epoch 15/25)
- **SoVITS weights**: `Evil_e16_s14032.pth` (82 MB, step 14032/21048)

## Configuration

### GPT-SoVITS Server Config (`tts_infer.yaml`)

The GPT-SoVITS api_v2.py needs a `tts_infer.yaml` config pointing to the model weights:

```yaml
# GPT_SoVITS/configs/tts_infer.yaml
custom:
  device: cuda
  is_half: true
  version: v2
  t2s_weights_path: E:/BaiduNetdiskDownload/Model/Evil/Evil-V2/GPT_weights_v2/Evil-e15.ckpt
  vits_weights_path: E:/BaiduNetdiskDownload/Model/Evil/Evil-V2/SoVITS_weights_v2/Evil_e16_s14032.pth
```

### Anima Config (`config/services.yaml`)

```yaml
tts:
  gpt_sovits:
    type: gpt_sovits
    base_url: "http://127.0.0.1:9880"
    ref_audio_path: "E:/BaiduNetdiskDownload/Model/Evil/参考语音.wav"
    prompt_text: "I played Shovel Knight once. It turns out AI doesn't exactly have perfect hand-eye coordination."
    prompt_lang: "en"
    text_lang: "en"
    top_k: 15
    top_p: 1.0
    temperature: 1.0
    media_type: "wav"
    streaming_mode: false
```

### Anima Service Selection (`config/config.yaml`)

```yaml
services:
  tts: gpt_sovits   # Switch from kokoro_glados to gpt_sovits
```

## Architecture

```
GPT-SoVITS Server (Windows)
  tts_infer.yaml ──→ Evil V2 weights
  api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
        │
        ▼ (HTTP /tts endpoint)
Anima
  config.yaml: services.tts: gpt_sovits
  services.yaml: tts.gpt_sovits → ref_audio + prompt
        │
        ▼
  TTSFactory → GPTSoVITSTTS → httpx.AsyncClient → POST /tts
```

## Goals / Non-Goals

**Goals:**
- Configure all files needed to use Evil voice in Anima
- Test TTS endpoint with curl to verify the model works

**Non-Goals:**
- Training or fine-tuning the model
- Modifying any Anima Python code
- Adding new provider types

## Decisions

### Use V2 over V1

V2 has more epoch choices (5/10/15/20/25 vs 8/16/24) and better model architecture. Recommend epoch 15 / step 14032 as a balanced checkpoint.

### English language config

The reference text and prompt are in English, so `prompt_lang: en` and `text_lang: en` are set explicitly.
