## Why

Adding `system.gpt_sovits` to `config.yaml` for the GPT-SoVITS startup integration causes a Pydantic `extra_forbidden` validation error because `SystemConfig` model doesn't define this field. Anima crashes on startup.

## What Changes

- Add `gpt_sovits: dict` field to `SystemConfig` in `src/anima/config/system.py`

## Capabilities

### New Capabilities
- None (bugfix)

### Modified Capabilities
- None

## Impact

- **Modified**: `src/anima/config/system.py` — add `gpt_sovits: dict = {}` field
- **Bugfix only**: No logic changes, no new features
