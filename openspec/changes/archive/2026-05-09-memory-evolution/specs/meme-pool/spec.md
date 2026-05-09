## ADDED Requirements

### Requirement: Active meme pool
The system SHALL maintain an active pool of exactly 10 memes (梗) ready for injection.

- MemePool SHALL be persisted in the `memes` SQLite table
- When the pool has fewer than 10 active memes, new candidates from PeriodicLearner or user input SHALL fill the slots
- When the pool has 10 active memes, new candidates SHALL undergo scoring comparison — if candidate score > lowest active score, the lowest is replaced

#### Scenario: Pool at capacity
- **WHEN** MemePool has 10 active memes and a new candidate with score 0.85 arrives
- **THEN** if the lowest active meme has score < 0.85, it is replaced by the new candidate

### Requirement: Meme lifecycle
Each meme SHALL follow a defined lifecycle: Generate → Store → Inject → Score → Discard/Resurrect.

- **Generate**: From PeriodicLearner (80%) or user frontend input (20%)
- **Store**: Persisted in `memes` table with initial `base_score = 0.7`
- **Inject**: Selected for LLM context based on context matching
- **Score**: After each injection, LLM evaluates effectiveness (0.0–1.0); score is averaged into `current_score`
- **Discard**: When replaced by higher-scoring candidate
- **Resurrect**: Discarded memes enter time-decay pool; if `effective_score > 0.6` after decay period and pool has slot, they come back

#### Scenario: Meme injection and scoring
- **WHEN** a meme is injected into an LLM response and the user responds positively
- **THEN** meme score increases (via LLM evaluation of response sentiment)

### Requirement: Meme injection context matching
Memes SHALL only be injected when the conversation context matches their `context_hint`.

- Context matching SHALL use keyword overlap between user input and meme's `context_hint`
- Injection SHALL be automatic in `streaming` personality mode
- Injection SHALL be opt-in (tool-call) in `default` personality mode
- Maximum 1 meme per response

#### Scenario: Context match
- **WHEN** user says "TypeScript又报错了" and a meme has context_hint containing "TypeScript"
- **THEN** the meme is eligible for injection

#### Scenario: Context mismatch
- **WHEN** user says "今天天气真好" and no meme context_hint matches
- **THEN** no meme is injected

### Requirement: Time-decay resurrection
Discarded memes SHALL support time-decay resurrection with configurable parameters.

- Decay function: `effective_score = base_score * (1 / (1 + e^(k * (t - t_half))))`
- Default: `k = 0.5`, `t_half = 7 days`
- Resurrection threshold: `effective_score > 0.6` AND pool has empty slot
- On resurrection, `base_score` increases by `+0.1` (max 1.0)
- `resurrection_count` SHALL be tracked; memes resurrected 3+ times SHALL be locked (permanent)

#### Scenario: Meme resurrection
- **WHEN** a meme with base_score=0.8 has been discarded for 7 days (t_half)
- **THEN** effective_score = 0.8 * 0.5 = 0.4, below threshold — not resurrected

#### Scenario: Strong meme comeback
- **WHEN** a meme with base_score=0.9 has been discarded for 14 days with t_half=7
- **THEN** effective_score = 0.9 * 0.12 = 0.108, will not resurrect without score increase

### Requirement: User-configured memes
Users SHALL be able to add memes via the frontend Meme Panel (20% source allocation).

- User memes SHALL have `source='user'` in the `memes` table
- User memes SHALL bypass AI discovery pipeline
- User memes SHALL start with `base_score = 0.8` (user preference bias)
- Users SHALL be able to edit, deactivate, or delete their memes at any time

#### Scenario: User adds a meme
- **WHEN** user enters meme text "你的逻辑链断在第...算了你自己找吧" with context_hint "当用户逻辑不清晰时"
- **THEN** a new meme with source='user' and base_score=0.8 is added to the pool
