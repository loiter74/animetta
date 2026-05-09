## ADDED Requirements

### Requirement: SystemConfig accepts gpt_sovits config

The `SystemConfig` Pydantic model SHALL accept a `gpt_sovits` dictionary field to prevent validation errors when the field is present in config.yaml.

#### Scenario: Config with gpt_sovits block loads without error

- **WHEN** `config.yaml` contains a `system.gpt_sovits` block with `path`, `python`, and `port` keys
- **THEN** `AppConfig.load()` SHALL succeed without raising a `ValidationError`
- **THEN** the `gpt_sovits` value SHALL be accessible as a dict

#### Scenario: Config without gpt_sovits block loads normally

- **WHEN** `config.yaml` does not contain `system.gpt_sovits`
- **THEN** `AppConfig.load()` SHALL succeed
- **THEN** `system.gpt_sovits` SHALL default to an empty dict `{}`
