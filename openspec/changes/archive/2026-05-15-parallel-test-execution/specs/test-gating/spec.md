## ADDED Requirements

### Requirement: CI pipeline split into fast and slow tracks
The GitHub Actions CI SHALL have two testing jobs: fast parallel tests and optional slow tests.

#### Scenario: Fast parallel tests as mandatory check
- **WHEN** a PR is opened or updated
- **THEN** the fast parallel test job SHALL run `pytest -n auto -m "not slow" --tb=short -q`
- **THEN** the result SHALL block PR merge if any tests fail

#### Scenario: Slow tests as optional check
- **WHEN** a developer triggers the slow test workflow
- **THEN** the slow test job SHALL run `pytest -m slow -n 0 --tb=short -q`
- **THEN** the result SHALL NOT block PR merge

### Requirement: Pre-existing test failures fixed
Tests that fail consistently due to platform assumptions or environment differences SHALL be fixed.

#### Scenario: Fix tracing exporter tests
- **WHEN** OTel Collector is not running
- **THEN** exporter tests SHALL gracefully handle the unavailable endpoint
- **THEN** tests SHALL pass without requiring a running Collector

#### Scenario: Fix platform-dependent path tests
- **WHEN** running on Windows
- **THEN** Linux-specific path tests SHALL be skipped with `@pytest.mark.skipif`
- **THEN** Windows path tests SHALL pass with the correct platform paths

### Requirement: CI must pass with zero failures
The fast parallel test job SHALL have zero expected failures.

#### Scenario: Post-fix verification
- **WHEN** all changes are applied
- **THEN** `PYTHONPATH=src python -m pytest tests/ -n auto -m "not slow" --tb=short -q` SHALL exit with code 0
