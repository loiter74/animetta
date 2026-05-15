## ADDED Requirements

### Requirement: Slow/hanging tests marked with @pytest.mark.slow
Tests that are known to hang, time out, or require external services SHALL be marked with `@pytest.mark.slow`.

#### Scenario: Mark test_bilibili_danmaku.py as slow
- **WHEN** `test_bilibili_danmaku.py` is examined
- **THEN** all test functions and classes in the file SHALL be marked with `@pytest.mark.slow`

### Requirement: Slow tests excluded from default run
Slow tests SHALL be excluded from the default parallel test run to prevent CI hangs.

#### Scenario: Default exclusion
- **WHEN** `pytest` is run without explicit flags
- **THEN** `-m "not slow"` SHALL be in the default addopts
- **THEN** slow tests SHALL NOT be collected or executed

#### Scenario: Explicit slow test run
- **WHEN** `pytest -m slow` is passed
- **THEN** only slow tests SHALL be collected and executed
- **THEN** slow tests SHALL run sequentially (no xdist) to avoid event loop conflicts

### Requirement: CI slow test job
The CI pipeline SHALL have a separate job for slow tests, triggered manually or on schedule.

#### Scenario: Manual trigger
- **WHEN** a developer triggers the slow test workflow manually
- **THEN** `pytest -m slow -n 0 --tb=short` SHALL be executed
- **THEN** the result SHALL NOT block PR merge

#### Scenario: Scheduled run
- **WHEN** the scheduled cron trigger fires (e.g., daily)
- **THEN** slow tests SHALL be executed and results reported
