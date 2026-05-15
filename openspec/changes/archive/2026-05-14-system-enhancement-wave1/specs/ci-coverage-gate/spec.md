## ADDED Requirements

### Requirement: Coverage threshold is enforced
The GitHub Actions test workflow SHALL include a coverage step with a configurable fail_under threshold.

#### Scenario: Coverage below threshold fails CI
- **WHEN** pytest --cov-report=term-missing runs with --cov-fail-under=70
- **THEN** coverage below 70% SHALL result in non-zero exit code

### Requirement: Coverage threshold starts at 70%, targets 80%
The initial fail_under SHALL be 70%, increasing to 80% as comprehensive-test-coverage completes.

#### Scenario: Current coverage meets minimum
- **WHEN** the current test suite runs with --cov-fail-under=70
- **THEN** coverage SHALL be at or above 70%

### Requirement: Coverage report is generated
The CI SHALL generate a coverage report as a workflow artifact.

#### Scenario: Coverage artifact available
- **WHEN** the test workflow completes
- **THEN** a coverage XML/HTML report SHALL be uploaded as a workflow artifact
