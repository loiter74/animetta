## ADDED Requirements

### Requirement: docs/README.md is updated
The file docs/README.md SHALL be updated to remove references to removed modules (adapters/, pipeline/, events/).

#### Scenario: No references to removed modules
- **WHEN** docs/README.md is scanned
- **THEN** it SHALL NOT reference adapters/, pipeline/, or events/ modules

### Requirement: AGENTS.md reflects current structure
The project AGENTS.md SHALL be updated to accurately describe the current codebase structure.

#### Scenario: Route handler references updated
- **WHEN** AGENTS.md mentions routes.py
- **THEN** it SHALL reference the new handler file structure (if routes-refactor is complete)
- **THEN** it SHALL accurately list testing frontend coverage stats

### Requirement: CHANGE_LOG is updated
Any notable project changes from this wave SHALL be recorded in the project's change log or equivalent documentation.

#### Scenario: Wave 1 changes documented
- **WHEN** a developer reads the project docs
- **THEN** they SHALL find documentation of frontend testing, route refactoring, and CI changes
