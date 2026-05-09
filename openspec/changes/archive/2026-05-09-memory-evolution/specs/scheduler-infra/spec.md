## ADDED Requirements

### Requirement: Lightweight asyncio scheduler
The system SHALL provide a lightweight `asyncio`-based scheduler for periodic tasks.

- Scheduler SHALL run as a background `asyncio.Task` within the main event loop
- Each scheduled task SHALL be defined as an async callable with configurable interval
- Tasks SHALL NOT block each other — independent tasks run concurrently
- Scheduler SHALL support add/remove/start/stop lifecycle
- Interval SHALL be configurable per task (seconds, minutes, or hours)

#### Scenario: Task registration
- **WHEN** a new periodic task is registered with interval=3600 seconds
- **THEN** the scheduler runs it every hour

#### Scenario: Graceful shutdown
- **WHEN** the application is shutting down
- **THEN** the scheduler cancels all pending tasks and waits for completion

### Requirement: Task timeout protection
Each scheduled task SHALL have a maximum execution time to prevent hang.

- Default timeout: 300 seconds (configurable per task)
- If a task exceeds its timeout, it SHALL be cancelled and a warning SHALL be logged
- The scheduler SHALL continue running other tasks unaffected

#### Scenario: Task timeout
- **WHEN** a PeriodicLearner consolidation task exceeds 300 seconds
- **THEN** the task is cancelled, a warning is logged, and other tasks continue

### Requirement: Configurable task schedules
Task intervals SHALL be configurable from `config/features/memory.yaml`:

```yaml
scheduler:
  enabled: true
  tasks:
    consolidate_conversations:
      interval: 3600  # seconds (1 hour)
      timeout: 120
    extract_patterns:
      interval: 86400  # 24 hours
      timeout: 300
    generate_meme_candidates:
      interval: 21600  # 6 hours
      timeout: 120
    maintain_meme_pool:
      interval: 3600  # 1 hour
      timeout: 30
    prune_learning_logs:
      interval: 86400  # 24 hours
      timeout: 60
```

#### Scenario: Config-driven schedule
- **WHEN** the application starts and scheduler is enabled
- **THEN** tasks are registered with intervals from config

### Requirement: Task metrics
The scheduler SHALL expose metrics for each task: last_run, last_duration, success/failure count.

- Metrics SHALL be accessible via the existing `StatsCallbackHandler` pattern
- Metrics SHALL be logged at `INFO` level after each task run

#### Scenario: Task metrics logging
- **WHEN** a consolidate_conversations task completes in 45 seconds
- **THEN** log entry: "[Scheduler] consolidate_conversations completed in 45.0s (success=12, failure=0)"
