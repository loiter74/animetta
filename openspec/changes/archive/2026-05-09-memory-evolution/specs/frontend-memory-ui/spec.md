## ADDED Requirements

### Requirement: Chat message persistence
The frontend SHALL persist chat messages locally using IndexedDB.

- All messages in the `chat` Pinia store SHALL be persisted after each message is complete
- On page load, the last session's messages SHALL be restored from IndexedDB
- Maximum persisted messages: 500 (configurable; oldest messages pruned first)
- Persistence SHALL be non-blocking — UI SHALL NOT wait for IndexedDB write

#### Scenario: Page reload
- **WHEN** user refreshes the page after a conversation
- **THEN** the last session's chat messages are restored from IndexedDB

#### Scenario: Message limit
- **WHEN** stored messages exceed 500
- **THEN** the oldest messages are pruned to stay within limit

### Requirement: Memory review panel
The frontend SHALL provide a collapsible "Memory Review" panel in the sidebar.

- Panel SHALL display fuzzy memories from the `fuzzy_memories` table
- Each fuzzy memory SHALL show: text, granularity badge (fact/persona/event), confidence score, timestamp
- Clicking a fuzzy memory SHALL reveal its source exact memories (via inverted index query)
- Panel SHALL have a search/filter bar (by text, granularity, date range)
- Data SHALL be fetched via Socket.IO event (`get_fuzzy_memories` / `fuzzy_memories_result`)

#### Scenario: Browse fuzzy memories
- **WHEN** user opens the Memory Review panel
- **THEN** a list of fuzzy memories is displayed, sorted by recency

#### Scenario: Drill down to source
- **WHEN** user clicks a fuzzy memory entry
- **THEN** the inverted index is queried and source exact memories are shown below

### Requirement: Meme management panel
The frontend SHALL provide a "Meme Manager" panel.

- Panel SHALL display all active memes with: text, score, use_count, source badge (AI/user)
- Users SHALL be able to add new memes (text + context_hint + tags)
- Users SHALL be able to rate/score individual memes (overrides AI score for that meme)
- Users SHALL be able to deactivate or delete memes
- Users SHALL be able to view discarded meme history (last 50)

#### Scenario: Add user meme
- **WHEN** user fills the "Add Meme" form with text and context hint
- **THEN** a new meme with source='user' is added to the MemePool

#### Scenario: Rate a meme
- **WHEN** user sets a meme's rating to 0.9
- **THEN** the meme's base_score is overridden to 0.9

### Requirement: Personality configuration panel
The frontend SHALL provide a "Personality" panel for runtime adjustments.

- Panel SHALL display current active personality mode and mood
- Users SHALL be able to switch between available persona YAML files
- Users SHALL be able to toggle streaming mode on/off
- Users SHALL be able to adjust memory_influence.weight slider (0.0–1.0)
- Changes SHALL take effect on next conversation turn

#### Scenario: Switch persona
- **WHEN** user selects a different persona from the dropdown
- **THEN** a `set_persona` Socket.IO event is emitted; orchestrator loads the new persona

#### Scenario: Adjust memory influence
- **WHEN** user moves the memory influence slider to 0.7
- **THEN** the system prompt personality section includes more memory-influenced traits

### Requirement: Socket.IO event extensions
The following new Socket.IO events SHALL be supported:

**Client → Server:**
- `get_fuzzy_memories`: Request fuzzy memories with optional filters
- `set_persona`: Change active persona YAML
- `set_personality_mode`: Override personality mode
- `meme_add`: Add a user meme
- `meme_rate`: Rate/score an existing meme
- `meme_delete`: Delete/deactivate a meme

**Server → Client:**
- `fuzzy_memories_result`: Response to `get_fuzzy_memories`
- `meme_added`: Confirmation of meme addition
- `meme_updated`: Confirmation of meme update
- `personality_updated`: Confirmation of personality change
- `memory.consolidation.progress`: Progress updates from PeriodicLearner

#### Scenario: Fuzzy memory request
- **WHEN** client emits `get_fuzzy_memories` with `{granularity: "event", limit: 20}`
- **THEN** server responds with `fuzzy_memories_result` containing matching fuzzy memories
