## ADDED Requirements

### Requirement: Async fuzzy memory consolidation
The system SHALL asynchronously consolidate conversation turns into fuzzy "I remember you said X about Y" format after each turn is stored.

- Granularity mix: fact-level 30%, persona-level 20%, event-level 50% (configurable)
- Consolidation SHALL run via `asyncio.create_task()` (non-blocking, fire-and-forget)
- Each fuzzy memory SHALL include a confidence score (0.0–1.0)
- Deep batch consolidation SHALL run on a configurable timer (default: every 10 turns or 1 hour)

#### Scenario: Single turn consolidation
- **WHEN** `output_node._store_conversation_to_memory()` completes
- **THEN** system creates a background task for fuzzy consolidation of that turn

#### Scenario: Batch consolidation
- **WHEN** 10 turns have accumulated without batch consolidation
- **THEN** system triggers deep batch consolidation analyzing all pending turns

### Requirement: Inverted index
The system SHALL maintain an inverted index mapping each fuzzy memory ID to its source exact memory IDs.

- Index entries SHALL include: `fuzzy_id`, `exact_type` (memory_turn | memory_entry | wiki_page), `exact_id`, `relevance` score
- Index SHALL be updated atomically when fuzzy memories are created
- Index SHALL be queryable from frontend for drill-down

#### Scenario: Index creation
- **WHEN** a fuzzy memory is consolidated from 3 source conversation turns
- **THEN** 3 inverted index entries are created linking the fuzzy ID to each source turn ID

#### Scenario: Frontend drill-down
- **WHEN** user clicks a fuzzy memory in the frontend panel
- **THEN** system queries the inverted index and displays the source exact memories

### Requirement: Hierarchical injection strategy
The LLM context injection SHALL support three tiers with automatic escalation based on user query depth.

- **Tier 1 — Context** (default): Inject only fuzzy narrative memories
- **Tier 2 — Supporting** (user query depth ≥ 2): Inject semi-precise summaries with confidence scores
- **Tier 3 — Ground Truth** (user query depth ≥ 4): Inject exact quotes with source references
- Query depth resets after each new conversation topic or session
- Query depth SHALL be tracked in `AgentState.metadata.user_query_depth`

#### Scenario: Normal conversation (Tier 1)
- **WHEN** user sends a message in a new conversation
- **THEN** system injects only Tier 1 fuzzy memories into the LLM context

#### Scenario: User follows up (Tier 2)
- **WHEN** user sends a follow-up message on the same topic (query_depth = 2)
- **THEN** system escalates to Tier 2, including supporting evidence with confidence scores

#### Scenario: User persists (Tier 3)
- **WHEN** user continues asking about the same topic (query_depth ≥ 4)
- **THEN** system escalates to Tier 3, injecting exact quotes and source references

### Requirement: Fuzzy memory storage
Fuzzy memories SHALL be persisted in SQLite `fuzzy_memories` table with the following schema:

- `id`: TEXT PRIMARY KEY (format: `fuzzy_{uuid4_short}`)
- `session_id`: TEXT NOT NULL
- `text`: TEXT NOT NULL (the fuzzy recall text)
- `granularity`: TEXT NOT NULL (fact | persona | event)
- `confidence`: REAL DEFAULT 0.7
- `source_turn_ids`: TEXT NOT NULL (JSON array of source turn IDs)
- `created_at`, `last_injected_at`, `injection_count`: timestamps and counters

#### Scenario: Store fuzzy memory
- **WHEN** consolidation produces a fuzzy memory with text "用户喜欢TypeScript的函数式风格"
- **THEN** a row is inserted with granularity='fact', confidence=0.85, source_turn_ids referencing the exact turns

### Requirement: Configurable consolidation parameters
The following parameters SHALL be configurable in `config/features/memory.yaml`:

- `fuzzy_memory.granularity_weights`: fact=0.3, persona=0.2, event=0.5
- `fuzzy_memory.consolidation.turns_per_lightweight`: 1 (every turn)
- `fuzzy_memory.consolidation.turns_per_deep`: 10
- `fuzzy_memory.consolidation.deep_interval_minutes`: 60
- `fuzzy_memory.injection.tier1_max_items`: 3
- `fuzzy_memory.injection.tier2_max_items`: 5
- `fuzzy_memory.injection.tier3_max_items`: 3
- `fuzzy_memory.injection.escalation_thresholds`: tier2_depth=2, tier3_depth=4

#### Scenario: Config reload
- **WHEN** config is updated and system is restarted
- **THEN** fuzzy memory system uses the new consolidation parameters
