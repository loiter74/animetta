## ADDED Requirements

### Requirement: Scheduled conversation summarization
The PeriodicLearner SHALL run on a configurable schedule to summarize unconsolidated conversations.

- Summarization SHALL use the configured LLM to produce structured daily summaries
- Output SHALL be stored in `learning_logs` table with `summary_type='conversation'`
- Summaries SHALL be written to `wiki/sources/` as proper AI-generated abstracts (not raw concatenation)
- Schedule interval SHALL be configurable (default: every 10 turns or 60 minutes)

#### Scenario: Daily summary generation
- **WHEN** PeriodicLearner triggers conversation summarization
- **THEN** unconsolidated turns are LLM-summarized into a structured daily abstract

#### Scenario: Summary persistence
- **WHEN** a conversation summary is generated
- **THEN** it is stored in `learning_logs` table and also written to the corresponding wiki source page

### Requirement: Pattern extraction
The PeriodicLearner SHALL extract behavioral patterns, preferences, and recurring themes from consolidated conversations.

- Pattern extraction SHALL run daily (default: every 24 hours)
- Patterns SHALL include: user preferences, communication style observations, recurring topics, emotional patterns
- Output SHALL be stored in `learning_logs` with `summary_type='pattern'`
- High-confidence patterns SHALL trigger wiki synthesis page creation or update

#### Scenario: Pattern discovery
- **WHEN** user mentions "TypeScript" in 5+ conversations over 3 days
- **THEN** PeriodicLearner extracts pattern "用户对TypeScript有持续兴趣" and stores it

### Requirement: Meme candidate generation
The PeriodicLearner SHALL generate meme candidates from extracted patterns and conversation highlights.

- Meme candidate generation SHALL run every 6 hours (configurable)
- Candidates SHALL be stored in `learning_logs` with `summary_type='meme_candidate'`
- Each candidate SHALL include: text, context_hint, confidence score
- High-confidence candidates SHALL be automatically added to MemePool (if slots available)

#### Scenario: Meme candidate from pattern
- **WHEN** a pattern "用户喜欢吐槽TypeScript类型系统" is extracted
- **THEN** PeriodicLearner generates meme candidate "类型体操警告" with context_hint "当用户提到TypeScript时"

#### Scenario: Meme pool injection
- **WHEN** a meme candidate has confidence > 0.7 AND MemePool has < 10 active memes
- **THEN** the candidate is automatically added to the MemePool

### Requirement: Learning log management
The `learning_logs` table SHALL be pruned periodically to prevent unbounded growth.

- Logs older than 90 days SHALL be automatically deleted (configurable retention period)
- High-value patterns SHALL be promoted to wiki synthesis pages before deletion
- Pruning SHALL be part of the daily maintenance cycle

#### Scenario: Log retention
- **WHEN** a learning log entry reaches 90 days old
- **THEN** it is eligible for pruning; if it contains a high-value pattern, it is first promoted to wiki
