## ADDED Requirements

### Requirement: AppConfig YAML loading
AppConfig SHALL correctly load and parse YAML configuration files.

#### Scenario: from_yaml loads full config
- **WHEN** from_yaml() is called with a valid YAML path
- **THEN** it SHALL return a fully populated AppConfig instance

#### Scenario: from_yaml expands environment variables
- **WHEN** YAML contains ${VAR} patterns
- **THEN** they SHALL be expanded from environment

#### Scenario: get_persona loads from file
- **WHEN** get_persona() is called
- **THEN** it SHALL load the persona YAML and return PersonaConfig

#### Scenario: get_system_prompt builds prompt
- **WHEN** get_system_prompt() is called
- **THEN** it SHALL build a system prompt string from persona config

#### Scenario: validate checks registered providers
- **WHEN** validate() is called
- **THEN** it SHALL verify all configured providers are registered

### Requirement: PersonaConfig construction
PersonaConfig SHALL correctly build system prompts from personality definitions.

#### Scenario: build_system_prompt includes traits
- **WHEN** build_system_prompt() is called
- **THEN** it SHALL include personality traits in the prompt

#### Scenario: build_system_prompt includes behavior rules
- **WHEN** build_system_prompt() is called
- **THEN** it SHALL include behavior rules in the prompt

### Requirement: ProviderRegistry functionality
ProviderRegistry SHALL correctly manage provider registration and creation.

#### Scenario: register stores config class
- **WHEN** @register() is called with category and type
- **THEN** the config class SHALL be stored in _configs dict

#### Scenario: register_service stores service class
- **WHEN** @register_service() is called
- **THEN** the service class SHALL be stored in _services dict

#### Scenario: create_service instantiates from config
- **WHEN** create_service() is called with valid category and config
- **THEN** it SHALL call from_config on the registered service class

#### Scenario: create_service raises on unknown
- **WHEN** create_service() is called with unregistered category/type
- **THEN** it SHALL raise ValueError

#### Scenario: create_union_type builds discriminated union
- **WHEN** create_union_type() is called for a category
- **THEN** it SHALL return an Annotated Union with Field(discriminator="type")

### Requirement: UserSettings persistence
UserSettings SHALL persist and reload user preferences.

#### Scenario: save writes to file
- **WHEN** save() is called with settings data
- **THEN** it SHALL write to the user settings file

#### Scenario: load reads saved settings
- **WHEN** load() is called after save
- **THEN** it SHALL return the previously saved settings
