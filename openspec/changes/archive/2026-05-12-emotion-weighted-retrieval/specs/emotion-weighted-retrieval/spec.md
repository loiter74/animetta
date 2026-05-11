## ADDED Requirements

### Requirement: Memory retrieval SHALL weight results by emotion tags

The system SHALL use emotion labels on MemoryEntry objects to boost retrieval ranking for high-emotion memories and suppress low-emotion ones.

#### Scenario: High-emotion memory ranks higher
- **WHEN** a memory has a high emotion value (e.g., "surprised", "angry")
- **AND** a semantically similar memory has no emotion tag
- **THEN** the high-emotion memory SHALL receive a ranking boost in search results

#### Scenario: Emotion weight decays slower for high emotions
- **WHEN** a memory has high emotion value
- **THEN** its retrieval weight SHALL decay slower than low-emotion memories
- **AND** the decay rate SHALL be inversely proportional to emotion intensity

#### Scenario: No emotion tag — no penalty
- **WHEN** a MemoryEntry has no emotion tag
- **THEN** the system SHALL apply neutral ranking (no boost, no penalty)
