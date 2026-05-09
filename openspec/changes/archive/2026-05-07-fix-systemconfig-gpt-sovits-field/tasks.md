## 1. Fix Pydantic Model

- [x] 1.1 Add `gpt_sovits: dict = Field(default={}, description="GPT-SoVITS server config")` to `SystemConfig` class

## 2. Verify

- [x] 2.1 Run python import check: `from anima.config.app import AppConfig` — OK
- [x] 2.2 Load config.yaml and verify no validation error — `gpt_sovits={'path': '', 'python': '', 'port': 9880}` — no error
- [x] 2.3 Confirm `start_gpt_sovits()` still reads gpt_sovits config correctly — path='', python='', port=9880
