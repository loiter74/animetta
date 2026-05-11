## ADDED Requirements

### Requirement: PeriodicLearner SHALL extract structured facts from conversation logs

The system SHALL, on a scheduled interval, run an LLM call over recent conversation logs to extract structured facts (preferences, identities, experiences, opinions, behaviors, goals) and persist them into Wiki Memory.

#### Scenario: Scheduled fact extraction from recent turns
- **WHEN** PeriodicLearner triggers an extraction cycle
- **THEN** the system reads the last N turns from conversation logs
- **AND** calls LLM with a structured extraction prompt
- **AND** writes valid extracted facts to Wiki Markdown files

#### Scenario: Fact deduplication and update
- **WHEN** extracted facts overlap with existing Wiki entries
- **THEN** the system SHALL merge new facts into existing entries (update old, add new)
- **AND** SHALL NOT create duplicate entries with identical content

#### Scenario: Extraction failure is non-blocking
- **WHEN** LLM extraction call fails
- **THEN** the system SHALL log the error and continue normal operation
- **AND** SHALL NOT affect real-time conversation response
