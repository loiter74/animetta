## 1. Config Class

- [x] 1.1 Create `src/anima/config/providers/tts/gpt_sovits.py` with `GPTSoVITSConfig` class, registered with `@ProviderRegistry.register("tts", "gpt_sovits")`, inheriting from `TTSBaseConfig`, with `type: Literal["gpt_sovits"]` and all parameters from the spec (base_url, ref_audio_path, prompt_text, prompt_lang, text_lang, top_k, top_p, temperature, speed, media_type, streaming_mode, text_split_method, sample_steps, seed)

## 2. Implementation Class

- [x] 2.1 Create `src/anima/services/speech/tts/gpt_sovits_tts.py` with `GPTSoVITSTTS` class, registered with `@ProviderRegistry.register_service("tts", "gpt_sovits")`, implementing `TTSInterface`
- [x] 2.2 Implement `__init__()` to store config params and create `httpx.AsyncClient` with base_url
- [x] 2.3 Implement `_call_api(text, **kwargs)` private method that sends POST to `/tts` with GPT-SoVITS request payload
- [x] 2.4 Implement `synthesize()` method that calls `_call_api()` and returns WAV audio bytes or file path
- [x] 2.5 Implement `close()` to properly close the HTTP client
- [x] 2.6 Implement `from_config()` classmethod for ProviderRegistry instantiation

## 3. Factory Registration

- [x] 3.1 Add `gpt_sovits` branch to `TTSFactory._build_config()` in `src/anima/services/speech/tts/factory.py`

## 4. Config Union Registration

- [x] 4.1 Add `GPTSoVITSConfig` import and entry to `TTSConfig` union type in `src/anima/config/providers/tts/__init__.py`

## 5. Configuration

- [x] 5.1 Add `gpt_sovits` entry to `config/services.yaml` with sample configuration and comments

## 6. Verification

- [x] 6.1 Run syntax check on all new/modified files - all pass
- [x] 6.2 Verify the provider appears in `TTSFactory.get_available_providers()` output - confirmed `gpt_sovits` registered
- [x] 6.3 Run the test suite to ensure no regressions: 158 passed, 1 failed (pre-existing audio analyzer test, unrelated to this change)
