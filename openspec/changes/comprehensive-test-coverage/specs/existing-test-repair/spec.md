## ADDED Requirements

### Requirement: AudioAnalyzer test dependencies
AudioAnalyzer tests SHALL have pydub available in test environment.

#### Scenario: pydub installed resolves fixture failures
- **WHEN** pydub is installed
- **THEN** AudioAnalyzer SHALL initialize without RuntimeError

### Requirement: MemoryEntryStore table initialization
MemoryEntryStore SHALL create required tables on initialization.

#### Scenario: memory_relations table created on init
- **WHEN** MemoryEntryStore is initialized
- **THEN** memory_relations table SHALL exist

#### Scenario: add_relation writes to table
- **WHEN** add_relation() is called after proper init
- **THEN** it SHALL insert a row into memory_relations without error

### Requirement: OutputNode volume computation
OutputNode volume computation SHALL handle missing pydub gracefully.

#### Scenario: _compute_volumes returns empty list when pydub missing
- **WHEN** pydub is not installed
- **THEN** _compute_volumes() SHALL return empty list without crash

#### Scenario: _trim_leading_silence returns None when pydub missing
- **WHEN** pydub is not installed
- **THEN** _trim_leading_silence() SHALL return None without crash
