## ADDED Requirements

### Requirement: All built-in emotion analyzers accept the same config parameters
The `EmotionAnalyzerFactory` passes the same `config` dict to all analyzer constructors. Every built-in analyzer SHALL accept `valid_emotions` as an optional constructor parameter to prevent TypeError.

#### Scenario: KeywordAnalyzer created with valid_emotions config
- **WHEN** `EmotionAnalyzerFactory.create("keyword_analyzer", config={"valid_emotions": ["happy", "sad", "angry"]})` is called
- **THEN** the factory SHALL successfully instantiate a `KeywordAnalyzer` without raising TypeError
- **THEN** the resulting analyzer SHALL have the same `extract()` behavior as the default constructor

#### Scenario: All built-in analyzers survive factory creation
- **WHEN** `EmotionAnalyzerFactory.create(name, config={"valid_emotions": [...]})` is called for each built-in analyzer name
- **THEN** the factory SHALL NOT raise an unexpected keyword argument error for `valid_emotions`
- **THEN** each analyzer SHALL be an instance of `IEmotionAnalyzer`

