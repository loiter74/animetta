## ADDED Requirements

### Requirement: pytest-xdist installed as dev dependency
The project SHALL install `pytest-xdist` as a development dependency.

#### Scenario: pip install
- **WHEN** `pip install pytest-xdist` is run
- **THEN** the `pytest-xdist` package SHALL be available and importable

### Requirement: Default parallel execution
The test suite SHALL default to parallel execution using all available CPU cores.

#### Scenario: -n auto in pyproject.toml
- **WHEN** `pytest` is run without explicit `-n` flag
- **THEN** it SHALL use `-n auto` from `pyproject.toml` addopts
- **THEN** tests SHALL be distributed across all available CPU cores

#### Scenario: Explicit worker count override
- **WHEN** `pytest -n 4` is passed on the command line
- **THEN** it SHALL use 4 workers regardless of CPU count

### Requirement: Sequential group isolation
Tests that share mutable state SHALL be grouped into sequential execution groups to prevent write conflicts.

#### Scenario: xdist_group marking
- **WHEN** a test file is marked with `@pytest.mark.xdist_group("serial")`
- **THEN** all tests in that group SHALL execute sequentially on a single worker
- **THEN** no two tests from the same group SHALL run concurrently

### Requirement: Pass/fail reporting with xdist
The test report SHALL clearly indicate which tests passed, failed, or were skipped under parallel execution.

#### Scenario: Standard output preserved
- **WHEN** tests run with xdist
- **THEN** failure output SHALL include the worker ID and test name
- **THEN** the summary line SHALL show total passed/failed/skipped counts
