## ADDED Requirements

### Requirement: Multi-layer personality architecture
The personality system SHALL support four layers stacked in priority order:

1. **Core Identity** (base): Static persona YAML definition — unchanged from current system
2. **Mood State** (dynamic): Current emotional state affecting expression — derived from emotion_node output
3. **Memory-Influenced Traits** (adaptive): Personality traits that shift based on accumulated memories
4. **Streaming Mode** (contextual): Separate personality behavior for livestream/danmaku interactions

Priority (highest to lowest): Streaming Mode > Mood State > Memory-Influenced > Core Identity

#### Scenario: Mood state override
- **WHEN** emotion_node detects 'happy' and personality shell has a happy mood override defined
- **THEN** the happy mood traits are merged on top of core identity

#### Scenario: Streaming mode activation
- **WHEN** the current session is a Bilibili danmaku session
- **THEN** streaming mode personality is activated (shorter replies, higher meme injection rate)

### Requirement: Personality prompt assembly
The personality shell SHALL produce a merged system prompt section at runtime.

- Each layer SHALL contribute prompt text that is concatenated with clear section markers
- Conflicting instructions SHALL be resolved by priority (higher priority layers override lower)
- The assembled personality prompt SHALL be injected before memory context in the final system prompt

#### Scenario: Prompt assembly
- **WHEN** Core Identity says "回复控制在60字以内" and Mood State says "开心时可以多说一点"
- **THEN** the merged prompt reflects the mood state override when applicable

### Requirement: Runtime personality switching
The system SHALL support switching personality layers at runtime without server restart.

- Streaming mode SHALL be toggled by session type (Bilibili vs direct chat)
- Mood state SHALL be updated per conversation turn (from emotion_node)
- Memory-influenced traits SHALL be recalculated when PeriodicLearner produces new patterns
- Frontend SHALL be able to force a specific personality mode

#### Scenario: Session-based switching
- **WHEN** a new danmaku arrives from Bilibili session
- **THEN** the orchestrator applies streaming mode personality for that turn

### Requirement: Personality config extension
The persona YAML format SHALL be extended with new optional sections (backward compatible):

```yaml
personality:
  # existing fields...
  
  # NEW: Mood overrides (optional)
  mood_states:
    happy:
      speaking_style: "更活泼，可以多表达正面情绪"
      max_length: 100
    sad:
      speaking_style: "温和，带安慰语气"
      max_length: 60
  
  # NEW: Streaming mode (optional)
  streaming_mode:
    reply_max_length: 40
    meme_injection_rate: 0.7
    danmaku_style: "简短有力，适合弹幕互动"
  
  # NEW: Memory influence (optional)
  memory_influence:
    weight: 0.3  # 0.0 = no influence, 1.0 = fully memory-driven
```

All new sections SHALL be optional — existing persona files SHALL continue to work unchanged.

#### Scenario: Existing persona compatibility
- **WHEN** an existing persona YAML without mood_states/streaming_mode is loaded
- **THEN** the personality shell uses defaults for missing sections (memory_influence.weight = 0)
