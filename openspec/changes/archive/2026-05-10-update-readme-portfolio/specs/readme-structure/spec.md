## ADDED Requirements

### Requirement: README uses 5-layer progressive structure
The README SHALL organize content into 5 progressively deeper layers: Hero (first impression), User Experience (what it does), Architecture (how it's built), Engineering (why it's trustworthy), and Action (how to try it). Each layer SHALL be separated by a horizontal rule (`---`).

#### Scenario: Reader scans from top to bottom
- **WHEN** a reader opens the README
- **THEN** they encounter the demo GIF and hook within the first scroll viewport
- **AND** they can progressively scroll deeper to find architecture diagrams, ADR summaries, and engineering metrics

### Requirement: Hero section displays demo GIF and project identity
The Hero section SHALL display a centered demo GIF at `assets/demo/anima-chat-preview.gif`, a one-line project hook describing Anima as an AI VTuber with Live2D and real-time voice, and a row of CI/quality badges (test status, Docker, Python versions, license, test count).

#### Scenario: Demo GIF is present
- **WHEN** a reader opens the README
- **THEN** the demo GIF is displayed prominently at the top
- **AND** if the GIF file is missing, a placeholder comment indicates where to add it

### Requirement: Architecture section includes C4 diagram and LangGraph state machine
The Architecture section SHALL include a mermaid C4 Level 1 system context diagram (reused from ARCHITECTURE.md), an ASCII data flow diagram showing the request lifecycle, and a description of the LangGraph state machine with its 7 nodes and conditional edges.

#### Scenario: Interviewer evaluates architecture
- **WHEN** an interviewer scrolls to the Architecture section
- **THEN** they can see a system-level diagram showing frontend, backend, external services, and data stores
- **AND** they can understand the data flow from user input through ASR/LLM/TTS/Emotion to output

### Requirement: Engineering section surfaces ADRs and quality metrics
The Engineering section SHALL include a table of all 5 Architecture Decision Records (ADR-001 through ADR-005) with decision titles and significance, and a metrics summary showing test count (81), CI status, type checking (mypy), linting (ruff), OpenTelemetry observability, and code scale (202 files, 30K lines).

#### Scenario: Interviewer evaluates engineering maturity
- **WHEN** an interviewer reads the Engineering section
- **THEN** they can see documented architecture decisions with links to full ADRs
- **AND** they can see quantitative metrics demonstrating project scale and quality practices

### Requirement: Provider support displayed as compact capability matrix
The provider support information SHALL be displayed as a single compact table listing LLM, ASR, TTS, and VAD providers, replacing the current three separate feature tables.

#### Scenario: Reader wants to know supported AI models
- **WHEN** a reader looks for supported AI providers
- **THEN** they can see all LLM, ASR, TTS, and VAD options in one consolidated table

### Requirement: Subtitle feature condensed to one table row
The bilingual subtitle feature SHALL be described in a single table row within the character features section, replacing the current 30-line dedicated section.

#### Scenario: Reader looks for subtitle feature
- **WHEN** a reader wants to know about subtitle support
- **THEN** they find a concise description in the character features table
- **AND** detailed usage instructions remain in the application's Settings UI

### Requirement: Bilingual CN/EN text maintained throughout
All section headers, feature descriptions, and key content SHALL be presented in both Chinese and English, using the pattern `**CN:** text **EN:** text` for compact items and separate lines for longer descriptions.

#### Scenario: Chinese-speaking interviewer reads README
- **WHEN** a Chinese-speaking reader opens the README
- **THEN** all key information is available in Chinese without switching languages

### Requirement: All existing commands preserved
The Quick Start, Docker deployment, testing, type checking, and linting command blocks SHALL be preserved exactly as they appear in the current README.

#### Scenario: Developer follows setup instructions
- **WHEN** a developer copies and runs the Quick Start commands
- **THEN** the commands work identically to the current README
