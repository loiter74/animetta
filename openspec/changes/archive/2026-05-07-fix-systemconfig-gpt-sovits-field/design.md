## Context

`SystemConfig` uses `BaseConfig` which has `extra="forbid"`. Any field in `config.yaml` under `system:` must be explicitly defined in the Pydantic model.

## Fix

Add `gpt_sovits` field to `SystemConfig` with a default empty dict, allowing the YAML config to pass validation while the startup script reads it directly via `get_gpt_sovits_config()`.

```python
class SystemConfig(BaseConfig):
    host: str = Field(default="localhost", description="Server address")
    port: int = Field(default=12394, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    gpt_sovits: dict = Field(default={}, description="GPT-SoVITS server config")
```

## Data Flow

```
config.yaml → AppConfig.from_yaml()
  ↓
SystemConfig.gpt_sovits = {"path": "", "python": "", "port": 9880}
  ↓ (validated, no error)
scripts/start/services.py → get_gpt_sovits_config() reads from yaml directly
```
