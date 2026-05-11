## ADDED Requirements

### Requirement: MemoryEntry SHALL decay in retrieval weight over time

The system SHALL apply a decay function to MemoryEntry objects that reduces retrieval ranking based on time since creation, emotion value, and retrieval frequency.

#### Scenario: Old low-emotion memory decays
- **WHEN** a MemoryEntry has low emotion value and has not been retrieved recently
- **THEN** its retrieval weight SHALL decrease over time
- **AND** SHALL eventually be archived (marked, not deleted)

#### Scenario: High-emotion memory resists decay
- **WHEN** a MemoryEntry has high emotion value
- **THEN** its decay rate SHALL be significantly slower
- **AND** frequent retrieval SHALL further slow decay ("consolidation")

#### Scenario: Archived memories are excluded from search
- **WHEN** a MemoryEntry's decay score drops below archive threshold
- **THEN** the system SHALL mark it as archived
- **AND** archived memories SHALL be excluded from default search results
- **AND** SHALL remain accessible in Wiki Markdown for audit trail
