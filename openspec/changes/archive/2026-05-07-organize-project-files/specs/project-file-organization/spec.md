## ADDED Requirements

### Requirement: Persona XML consistency

The XML persona file SHALL be kept and its content SHALL match the YAML persona to ensure format diversity without content contradiction.

#### Scenario: XML matches analyst persona

- **WHEN** a developer reads `config/personas/neuro-vtuber.xml`
- **THEN** its content SHALL describe the analyst persona, not the old VTuber persona
- **THEN** the XML format SHALL be preserved as an alternative prompt template format

### Requirement: Remove redundant files

Files whose content is fully duplicated elsewhere SHALL be removed to avoid confusion.

#### Scenario: ref_text.txt removed

- **WHEN** examining `config/gpt_sovits/evil/`
- **THEN** `ref_text.txt` SHALL NOT exist (its content is in `config/services.yaml` as `prompt_text`)
