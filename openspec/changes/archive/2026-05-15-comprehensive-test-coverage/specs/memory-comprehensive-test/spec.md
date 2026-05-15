## ADDED Requirements

### Requirement: Wiki organizer topology operations
WikiOrganizer SHALL perform correct page organization operations.

#### Scenario: organize collects pages and builds relationship graph
- **WHEN** organize() is called with wiki pages
- **THEN** it SHALL build a relationship graph between pages

#### Scenario: LLM-based merge combines related pages
- **WHEN** merge_pages() is called with related pages
- **THEN** it SHALL produce a merged page with combined content

#### Scenario: rule-based fallback works without LLM
- **WHEN** LLM suggestion fails
- **THEN** it SHALL fall back to rule-based organization

#### Scenario: rebuild_index generates index page
- **WHEN** rebuild_index() is called
- **THEN** it SHALL write an index.md with all page links

### Requirement: Learner engine scheduled tasks
PeriodicLearner SHALL execute scheduled knowledge extraction tasks.

#### Scenario: consolidate_conversations creates summaries
- **WHEN** consolidate_conversations() is called
- **THEN** it SHALL create conversation summaries

#### Scenario: extract_patterns identifies patterns
- **WHEN** extract_patterns() is called
- **THEN** it SHALL identify behavioral patterns

#### Scenario: generate_meme_candidates proposes memes
- **WHEN** generate_meme_candidates() is called
- **THEN** it SHALL produce meme candidates

#### Scenario: extract_facts processes in batch
- **WHEN** extract_facts() is called
- **THEN** it SHALL extract facts from turns and write to wiki

#### Scenario: prune_logs removes old entries
- **WHEN** prune_logs() is called
- **THEN** it SHALL remove old log entries beyond retention period

### Requirement: FuzzyLayer context building
FuzzyLayer SHALL build fuzzy context from wiki and short-term memory.

#### Scenario: build_fuzzy_context returns tiered narratives
- **WHEN** build_fuzzy_context() is called with session data
- **THEN** it SHALL return narratives for all 3 tiers

#### Scenario: cache TTL expires after 5 minutes
- **WHEN** build_fuzzy_context() is called twice within 5min
- **THEN** second call SHALL return cached result
- **WHEN** called after 5min TTL
- **THEN** it SHALL rebuild the context

### Requirement: FactExtractor atomic fact extraction
FactExtractor SHALL extract atomic facts from conversation turns.

#### Scenario: extract identifies key information
- **WHEN** extract() is called with a MemoryTurn containing personal info
- **THEN** it SHALL return a list of MemoryEntry facts

#### Scenario: version chain detects unchanged content
- **WHEN** extract() is called with same content as existing fact
- **THEN** it SHALL NOT create a new version

#### Scenario: relation analysis determines UPDATES/EXTENDS/DERIVES
- **WHEN** new fact relates to existing fact
- **THEN** it SHALL set appropriate relation type

### Requirement: Wiki ingestor full pipeline
WikiIngestor SHALL execute the complete ingest workflow.

#### Scenario: ingest_turn writes raw log
- **WHEN** ingest_turn() is called with a turn
- **THEN** it SHALL append to raw/YYYY-MM-DD.md

#### Scenario: ingest_turn scores importance
- **WHEN** ingest_turn() is called
- **THEN** it SHALL calculate importance score for the turn

#### Scenario: ingest_turn updates wiki pages
- **WHEN** high-importance turn is ingested
- **THEN** relevant wiki entity/concept pages SHALL be created or updated

### Requirement: ShortTermMemory FIFO management
ShortTermMemory SHALL maintain conversational context within limits.

#### Scenario: append adds to deque
- **WHEN** append() is called
- **THEN** the turn SHALL be added to the end

#### Scenario: max_turns prunes oldest
- **WHEN** more than max_turns are appended
- **THEN** oldest turns SHALL be evicted

#### Scenario: get_context returns recent turns
- **WHEN** get_context() is called
- **THEN** it SHALL return the most recent turns

### Requirement: MemorySystem integration
MemorySystem SHALL wire all subsystems together for store/retrieve operations.

#### Scenario: store_turn chains through subsystems
- **WHEN** store_turn() is called
- **THEN** it SHALL score, store to short-term, ingest to wiki, and update fuzzy layer

#### Scenario: retrieve_context performs hybrid search
- **WHEN** retrieve_context() is called with a query
- **THEN** it SHALL perform hybrid search across Chroma and SQLite

#### Scenario: retrieve_context fetches user profile
- **WHEN** retrieve_context() is called
- **THEN** it SHALL include user profile in context
