## ADDED Requirements

### Requirement: StandaloneLLMTagAnalyzer extraction
The LLM tag analyzer SHALL correctly parse [emotion] tags from text.

#### Scenario: extract finds emotion tags
- **WHEN** extract() is called with "[happy] Hello"
- **THEN** it SHALL return emotion="happy" at the start of timeline

#### Scenario: extract returns cleaned text
- **WHEN** extract() is called with "[sad] I'm feeling down"
- **THEN** it SHALL return cleaned text without tags

#### Scenario: extract handles multiple tags
- **WHEN** extract() is called with text containing multiple emotion tags
- **THEN** it SHALL return a timeline with multiple emotion entries

#### Scenario: extract return neutral for no tags
- **WHEN** extract() is called with no emotion tags
- **THEN** it SHALL return emotion="neutral"

### Requirement: KeywordAnalyzer Chinese matching
The keyword analyzer SHALL detect emotions from Chinese keywords.

#### Scenario: happy keywords trigger happy emotion
- **WHEN** analyze() is called with happy Chinese keywords
- **THEN** it SHALL return emotion="happy" with high confidence

#### Scenario: sad keywords trigger sad emotion
- **WHEN** analyze() is called with sad Chinese keywords
- **THEN** it SHALL return emotion="sad"

#### Scenario: neutral for no matching keywords
- **WHEN** analyze() is called with neutral text
- **THEN** it SHALL return emotion="neutral"

### Requirement: EmotionParamMapper mapping
EmotionParamMapper SHALL correctly map emotions to Live2D parameters.

#### Scenario: happy maps to mouth and eyebrow params
- **WHEN** map_emotion() is called with "happy"
- **THEN** it SHALL return ParameterState with ParamMouthOpenY and ParamEyebrowLY values

#### Scenario: neutral returns zero values
- **WHEN** map_emotion() is called with "neutral"
- **THEN** it SHALL return near-zero parameter values

#### Scenario: angry maps to high intensity
- **WHEN** map_emotion() is called with "angry"
- **THEN** it SHALL return high-intensity ParameterState values

#### Scenario: random variance adds natural feel
- **WHEN** map_emotion() is called multiple times with same emotion
- **THEN** parameter values SHALL have slight random variance

### Requirement: Timeline strategy calculation
Timeline strategies SHALL correctly distribute emotions over time.

#### Scenario: PositionBasedStrategy evenly distributes
- **WHEN** calculate() is called with multiple emotions
- **THEN** each emotion SHALL get equal time allocation

#### Scenario: DurationBasedStrategy weights by emotion type
- **WHEN** calculate() is called
- **THEN** sad SHALL have 1.5x duration, surprised SHALL have 0.8x

#### Scenario: IntensityBasedStrategy weights by intensity
- **WHEN** calculate() is called
- **THEN** surprised SHALL have 0.95 intensity weight, neutral SHALL have 0.3

### Requirement: EmotionAnalyzerFactory
EmotionAnalyzerFactory SHALL create the correct analyzer type.

#### Scenario: create llm_tag_analyzer
- **WHEN** create("llm_tag_analyzer") is called
- **THEN** it SHALL return a StandaloneLLMTagAnalyzer instance

#### Scenario: create keyword_analyzer
- **WHEN** create("keyword_analyzer") is called
- **THEN** it SHALL return a KeywordAnalyzer instance

#### Scenario: create raises for unknown
- **WHEN** create() is called with unknown type
- **THEN** it SHALL raise ValueError

### Requirement: AudioAnalyzer volume envelope
AudioAnalyzer SHALL compute volume envelopes from audio data.

#### Scenario: valid audio produces volume envelope
- **WHEN** compute_volume_envelope() is called with valid WAV audio
- **THEN** it SHALL return a list of float values in [0, 1] range

#### Scenario: gain amplifies volume
- **WHEN** compute_volume_envelope() is called with gain > 1.0
- **THEN** output values SHALL be higher than without gain

#### Scenario: silent audio returns zeros
- **WHEN** compute_volume_envelope() is called with silent audio
- **THEN** it SHALL return all zeros
