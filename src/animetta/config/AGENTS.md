# CONFIG — PYDANTIC CONFIGURATION MODELS

**Generated:** 2026-05-23
**Commit:** 8930c5f

> Parent: [../AGENTS.md](../AGENTS.md) — backend-wide conventions.

## OVERVIEW
Pydantic V2 configuration layer. Mirrors services/ with provider config classes per type. YAML in config/ at project root → Pydantic validation here. Central provider registry via @ProviderRegistry decorator.

## STRUCTURE
```
config/
├── core/registry.py         # @ProviderRegistry — decorator-based service registration (ADR-003)
├── core/__init__.py          # Base config classes
├── providers/                # Provider configs mirroring services/ layout
│   ├── llm/                  # 8 files: base, deepseek, glm, openai, ollama, local_lora, mock + factory
│   ├── tts/                  # 11 files: base + core providers + contrib/ providers
│   ├── asr/                  # 7 files: base, faster_whisper, funasr, glm, openai, mock + factory
│   ├── vad/                  # 4 files: base, silero, mock + factory
│   ├── vc/                   # 4 files: base, rvc, mock + factory
│   └── separation/           # 4 files: base, demucs, mock + factory
├── persona/                  # Character personality models (base, enhanced)
├── data_models/              # Shared data models (meme)
├── app.py                    # AppConfig — main configuration (433 lines)
├── system.py                 # SystemConfig
├── agent.py                  # AgentConfig
├── user_settings.py          # UserSettings
├── live2d.py                 # Live2D config
├── singing_config.py         # Singing module config
└── prompts.py                # LLM prompt templates
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Register new provider | `core/registry.py` | `@ProviderRegistry.register_config("type", "name")` |
| Add provider config | `providers/{type}/` | Create Pydantic model, register via decorator |
| Change app settings | `app.py` | 433-line config schema |
| Persona model | `persona/` | YAML → Pydantic parsing |
| Provider config pattern | any `providers/*/base.py` | Base class with common fields + provider-specific subclass |

## KEY PATTERNS
- **@ProviderRegistry.register_config**: Decorator-based registration — no if/elif chains
- **Config ↔ Service pairing**: Every provider config at `config/providers/{type}/` mirrors an implementation at `services/{speech,intelligence}/{type}/`
- **YAML-driven**: `config/config.yaml` → `config/services.yaml` → Pydantic validation → runtime objects
- **Pydantic V2 only**: `model_config = ConfigDict(...)` — `class Config:` is forbidden

## ANTI-PATTERNS
- ❌ Never use `if/elif` for provider config selection — use `@ProviderRegistry`
- ❌ Never add a provider implementation without a corresponding config class here
- ❌ Pydantic V2 only — `class Config:` forbidden

## NOTES
- `app.py` (433 lines) is the main config schema — changes cascade to all subsystems
- Provider config structure exactly mirrors the service layout under `services/speech/` and `services/intelligence/`
- YAML files at project root `config/` are validated against models here
