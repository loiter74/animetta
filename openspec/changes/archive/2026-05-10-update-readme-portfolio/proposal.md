## Why

The current README is a flat feature list that fails to convey the project's engineering depth — critical for a portfolio project viewed by interviewers. It needs to guide readers from "what is this" to "how is it built" to "why it's trustworthy" in a progressive 5-layer structure.

## What Changes

- Restructure README into 5 progressive layers: Hero → User Experience → Architecture → Engineering Depth → Action
- Add mermaid C4 architecture diagram (from existing ARCHITECTURE.md)
- Highlight LangGraph state machine, plugin architecture with @ProviderRegistry, and hybrid search memory as key engineering signals
- Add ADR summary table showing 5 formal architecture decisions
- Add engineering maturity section: test count, CI/CD, type safety, observability, code scale
- Condense subtitle feature from 30-line dedicated section to one table row
- Consolidate provider support into a single capability matrix (LLM/ASR/TTS/VAD)
- Add demo GIF placeholder for user-recorded video
- Maintain bilingual CN/EN throughout
- **BREAKING**: Remove standalone "为什么选择 Anima" section — replaced by L2 user-facing highlights

## Capabilities

### New Capabilities
- `readme-structure`: Progressive 5-layer README structure (Hero → UX → Architecture → Engineering → Action) with mermaid diagrams, ADR table, and engineering maturity signals

### Modified Capabilities
<!-- No existing specs modified — this is a documentation-only change -->

## Impact

- Affected: `README.md` (complete rewrite, ~300 lines → ~200 lines with higher information density)
- References: `ARCHITECTURE.md` (mermaid diagrams reused), `docs/adrs/` (ADR summaries), `AGENTS.md` (anti-patterns cross-referenced)
- No code, API, or dependency changes
