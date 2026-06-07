## ADDED Requirements

### Requirement: Shared Chinese stopwords constant
The system SHALL define a single `STOPWORDS` frozenset in `services.bilibili.text_utils` containing Chinese stopwords for danmaku/comment filtering, imported by all modules that need it.

#### Scenario: Stopwords from single source
- **WHEN** `MemeCollector` and `DanmakuBuffer` both need to filter stopwords
- **THEN** they import `STOPWORDS` from `services.bilibili.text_utils` rather than defining their own copies

#### Scenario: Stopwords set is immutable
- **WHEN** any code receives the `STOPWORDS` reference
- **THEN** it is a `frozenset` and cannot be mutated at runtime

### Requirement: Tag string parsing
The system SHALL provide `parse_tags(tag_str) -> list[str]` that splits a comma-separated tag string into cleaned individual tags.

#### Scenario: Comma-separated tags
- **WHEN** `parse_tags("搞笑, 鬼畜, MAD")` is called
- **THEN** it returns `["搞笑", "鬼畜", "MAD"]`

#### Scenario: Empty input
- **WHEN** `parse_tags("")` is called
- **THEN** it returns an empty list

### Requirement: Title phrase extraction
The system SHALL provide `extract_title_phrases(title) -> list[str]` that splits a video title into candidate phrases using punctuation and length heuristics.

#### Scenario: Title with separators
- **WHEN** `extract_title_phrases("【MAD】进击的巨人×Unravel｜热血混剪")` is called
- **THEN** it returns extracted phrases like `["MAD", "进击的巨人", "Unravel", "热血混剪"]`

#### Scenario: Short title
- **WHEN** `extract_title_phrases("早安")` is called
- **THEN** it returns `["早安"]` (or empty if below 2-char minimum)
