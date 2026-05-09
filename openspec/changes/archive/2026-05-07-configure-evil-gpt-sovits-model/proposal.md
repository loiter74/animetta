## Why

Configure the Anima system to use a trained GPT-SoVITS voice model for the "Evil" character (English-speaking, Neuro-sama style), using V2 model weights and reference audio. This enables the AI companion to speak in Evil's trained voice via the GPT-SoVITS TTS provider.

## What Changes

- Create GPT-SoVITS V2 config (`tts_infer.yaml`) pointing to Evil V2 model weights at `E:\BaiduNetdiskDownload\Model\Evil\Evil-V2`
- Update Anima `config/services.yaml` to use `gpt_sovits` provider with reference audio and prompt text
- Update Anima `config/config.yaml` to switch TTS to `gpt_sovits`
- Optionally set `config.yaml` persona to align with Evil character

## Capabilities

### New Capabilities
- `evil-voice-profile`: Configuration profile for Evil GPT-SoVITS voice model, including GPT/SoVITS weight paths, reference audio, and Anima service binding

### Modified Capabilities
- None

## Impact

- **Modified**: `config/services.yaml` — add `gpt_sovits` instance config with Evil reference audio
- **Modified**: `config/config.yaml` — set `services.tts: gpt_sovits`
- **New file (GPT-SoVITS side)**: Evil V2 `tts_infer.yaml` config template in docs
- **No Anima code changes**: All changes are configuration only
