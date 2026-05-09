## ADDED Requirements

### Requirement: Evil voice model configuration

The system SHALL provide configuration for the "Evil" GPT-SoVITS V2 voice model, enabling Anima to synthesize speech in Evil's trained voice.

#### Scenario: GPT-SoVITS server uses correct weights

- **WHEN** the GPT-SoVITS `api_v2.py` starts with the `tts_infer.yaml` pointing to Evil V2 weights
- **THEN** the server SHALL load `Evil-e15.ckpt` as the GPT model
- **THEN** the server SHALL load `Evil_e16_s14032.pth` as the SoVITS model

#### Scenario: Anima uses correct reference audio

- **WHEN** Anima's `services.yaml` has `tts.gpt_sovits` configured with the Evil reference audio
- **THEN** each TTS request SHALL send the reference audio path `E:/BaiduNetdiskDownload/Model/Evil/参考语音.wav` to the GPT-SoVITS API
- **THEN** each TTS request SHALL send the prompt text for reference audio alignment

#### Scenario: English language synthesis

- **WHEN** Anima sends English text for TTS synthesis
- **THEN** the `text_lang` parameter SHALL be `en`
- **THEN** the `prompt_lang` parameter SHALL be `en`

#### Scenario: Verify TTS via curl

- **WHEN** a user sends a curl POST request to the GPT-SoVITS API with the Evil model loaded
- **THEN** the API SHALL return a valid WAV audio file containing speech in Evil's voice
